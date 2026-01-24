from datetime import datetime, timedelta
from typing import cast
import requests
from bs4 import BeautifulSoup
from amadeus import ResponseError

from src.models.state import AgentState
from src.models.schemas import TravelIntent
from src.services.llm_service import llm_service
from src.services.amadeus_service import amadeus_service
from src.utils.cache import airport_cache
from src.config.settings import EUR_TO_INR


def intent_node(state: AgentState):
    structured = llm_service.get_structured_llm(TravelIntent)

    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Build context from conversation history
    context = ""
    if state.conversation_history:
        context = "\n\nPrevious conversation:\n"
        for msg in state.conversation_history[-4:]:  # Last 4 messages
            context += f"{msg['role']}: {msg['content']}\n"
    
    raw = structured.invoke(
        f"""
Extract structured travel intent from the user query.
Use intent=clarify if anything required is missing.
Use intent=follow_up if the user is asking about previous results or making modifications to a previous query.

{context}

**IMPORTANT RULES:**
1. Return all dates in ISO format (YYYY-MM-DD).
   - If the user says "tomorrow", use: {tomorrow}
   - If the user says "today", use: {today}
   - If the user says "next week", use: {next_week}
   - If the user says "in X days/nights", calculate from today ({today}).

2. Field usage by intent type:
   - **flight_search**: origin = departure airport, destination = arrival airport, check_in = departure date
   - **hotel_search**: destination = hotel city code (NOT origin!), check_in = check-in date, check_out = check-out date
   - **both**: origin = departure, destination = arrival/hotel city, check_in = departure/check-in, check_out = check-out
   - **follow_up**: Extract any new parameters while keeping context from previous query

3. For hotel searches, ALWAYS put the city in the "destination" field, NOT "origin".

4. If user query is incomplete or ambiguous, use intent=clarify and explain what's missing in reasoning.

5. Common airport codes: Mumbai=BOM, Delhi=DEL, Bangalore=BLR, Chennai=MAA, Kolkata=CCU

Current Query: {state.query}
"""
    )

    if isinstance(raw, dict):
        intent_data = raw 
    else:
        intent_data = cast(TravelIntent, raw).model_dump()
    
    # =========================================
    # POST-PROCESSING VALIDATION (CRITICAL!)
    # =========================================
    
    original_intent = intent_data.get("intent")
    
    # Fix common mistakes for hotel searches
    if original_intent == "hotel_search":
        if intent_data.get("origin") and not intent_data.get("destination"):
            intent_data["destination"] = intent_data["origin"]
            intent_data["origin"] = None
    
    # STRICT VALIDATION FOR FLIGHT SEARCH
    if original_intent == "flight_search":
        missing = []
        
        # Check for origin
        if not intent_data.get("origin"):
            missing.append("departure city/airport")
        
        # Check for destination
        if not intent_data.get("destination"):
            missing.append("arrival city/airport")
        
        # Check if origin and destination are the same (likely an error)
        if (intent_data.get("origin") and 
            intent_data.get("destination") and 
            intent_data.get("origin") == intent_data.get("destination")):
            missing.append("arrival city/airport (cannot be same as departure)")
        
        # Check for departure date
        if not intent_data.get("check_in"):
            missing.append("departure/travel date")
        
        # If anything is missing, force clarify
        if missing:
            intent_data["intent"] = "clarify"
            intent_data["reasoning"] = f"Missing: {', '.join(missing)}"
            print(f"⚠️  Flight search validation failed: {intent_data['reasoning']}")
    
    # STRICT VALIDATION FOR HOTEL SEARCH
    if original_intent == "hotel_search":
        missing = []
        
        if not intent_data.get("destination"):
            missing.append("destination city")
        
        if not intent_data.get("check_in"):
            missing.append("check-in date")
        
        if not intent_data.get("check_out"):
            missing.append("check-out date")
        
        if missing:
            intent_data["intent"] = "clarify"
            intent_data["reasoning"] = f"Missing: {', '.join(missing)}"
            print(f"⚠️  Hotel search validation failed: {intent_data['reasoning']}")
    
    # STRICT VALIDATION FOR BOTH
    if original_intent == "both":
        missing = []
        
        if not intent_data.get("origin"):
            missing.append("departure city/airport")
        
        if not intent_data.get("destination"):
            missing.append("destination city")
        
        if not intent_data.get("check_in"):
            missing.append("check-in/departure date")
        
        if not intent_data.get("check_out"):
            missing.append("check-out date")
        
        if missing:
            intent_data["intent"] = "clarify"
            intent_data["reasoning"] = f"Missing: {', '.join(missing)}"
            print(f"⚠️  Combined search validation failed: {intent_data['reasoning']}")

    # Past-date guard
    if intent_data.get("check_in"):
        try:
            check_in_date = datetime.fromisoformat(intent_data["check_in"])
            if check_in_date.date() < datetime.now().date():
                intent_data["intent"] = "clarify"
                intent_data["reasoning"] = "Check-in/departure date cannot be in the past"
        except ValueError:
            intent_data["intent"] = "clarify"
            intent_data["reasoning"] = "Invalid date format. Please provide a valid date."
    
    # Debug output
    if intent_data.get("intent") == "clarify":
        print(f"🔄 Intent changed to CLARIFY: {intent_data.get('reasoning')}")

    return {"intent": intent_data}

def flight_tool(state: AgentState):
    if state.intent is None:
        return {"response": "Internal error: missing intent"}
    i = state.intent

    try:
        print(f"\n{'='*70}")
        print("FLIGHT SEARCH DEBUG - START")
        print(f"{'='*70}")
        print(f"📍 Origin: {i.get('origin')}")
        print(f"📍 Destination: {i.get('destination')}")
        print(f"📅 Departure Date: {i.get('check_in')}")
        print(f"👥 Travelers: {i.get('travelers')}")
        print(f"{'='*70}")
        
        # Validate required fields
        if not i.get("origin"):
            print("❌ ERROR: Missing origin")
            return {"flights": [], "response": "Missing origin airport code"}
        
        if not i.get("destination"):
            print("❌ ERROR: Missing destination")
            return {"flights": [], "response": "Missing destination airport code"}
        
        if not i.get("check_in"):
            print("❌ ERROR: Missing departure date")
            return {"flights": [], "response": "Missing departure date"}
        
        print("\n🚀 Making API call to Amadeus...")
        
        res_data = amadeus_service.search_flights(
            i["origin"],
            i["destination"],
            i["check_in"],
            i["travelers"]
        )
        
        print("\n✅ API Response Status: SUCCESS")
        print(f"📊 Number of flight offers: {len(res_data) if res_data else 0}")
        print(f"{'='*70}\n")
        
        return {"flights": res_data}
        
    except ResponseError as e:
        print(f"\n{'='*70}")
        print("❌ AMADEUS API ERROR - Checking for fallback")
        print(f"{'='*70}")
        
        error_dict = {}
        try:
            error_dict = e.response.result if hasattr(e, 'response') else {}
            print(f"Full Error Response: {error_dict}")
            
            if error_dict.get('errors'):
                error_code = error_dict['errors'][0].get('code')
                error_status = error_dict['errors'][0].get('status')
                
                # System error - API is down, use web search fallback
                if error_code == 141 or error_status == 500:
                    print("⚠️ API appears to be down (Error 141), using web search fallback...")
                    
                    # Get city names for better search
                    origin_city = airport_cache.get_city_name(i["origin"]) if i.get("origin") else i["origin"]
                    dest_city = airport_cache.get_city_name(i["destination"]) if i.get("destination") else i["destination"]
                    
                    # Format date nicely
                    try:
                        date_obj = datetime.fromisoformat(i["check_in"])
                        date_str = date_obj.strftime("%B %d, %Y")
                    except Exception:
                        date_str = i["check_in"]
                    
                    # Mark this as web search data
                    return {
                        "flights": [],
                        "response": None,
                        "use_web_search": True,
                        "search_query": f"flights from {origin_city} to {dest_city} on {date_str} price"
                    }
        except Exception as inner_e:
            print(f"Error parsing response: {inner_e}")
        
        print(f"{'='*70}\n")
        return {"flights": [], "response": f"Flight search error: {str(e)}"}
        
    except Exception as e:
        print(f"\n{'='*70}")
        print("❌ UNEXPECTED ERROR")
        print(f"{'='*70}")
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n")
        return {"flights": [], "response": f"Unexpected flight error: {str(e)}"}


def get_fallback_message(state: AgentState):
    """Generic fallback message when web search also fails"""
    i = state.intent or {}
    
    try:
        origin_city = airport_cache.get_city_name(i.get('origin', '')) if i.get('origin') else 'departure city'
    except Exception:
        origin_city = i.get('origin', 'departure city')
    
    try:
        dest_city = airport_cache.get_city_name(i.get('destination', '')) if i.get('destination') else 'destination city'
    except Exception:
        dest_city = i.get('destination', 'destination city')
    
    date = i.get('check_in', 'your selected date')
    
    return f"""
⚠️ **The flight booking API is temporarily unavailable and web search is also having issues.**

📋 **Your Search Details:**
- From: {origin_city}
- To: {dest_city}
- Date: {date}

💡 **What you can do:**
1. **Visit these sites directly:**
   - Google Flights: https://www.google.com/flights
   - Skyscanner: https://www.skyscanner.com
   - Kayak: https://www.kayak.com

2. **Check airline websites:**
   - Air India: https://www.airindia.in
   - IndiGo: https://www.goindigo.in
   - Vistara: https://www.airvistara.com

3. **Try again later** - The API should be back online soon!

🔄 I'll be able to provide real-time flight data once the API is restored.
"""


def web_search_fallback_node(state: AgentState):
    """Use SearXNG web search when Amadeus API is unavailable"""
    if not state.flights and state.use_web_search:
        search_query = state.search_query or ''
        
        if not search_query:
            return {"response": "Unable to search for flights at this time."}
        
        print(f"🔍 Performing web search: {search_query}")
        
        # List of public SearXNG instances (fallback if one fails)
        searxng_instances = [
            "https://searx.be/search",
            "https://search.bus-hit.me/search",
            "https://searx.tiekoetter.com/search",
            "https://paulgo.io/search"
        ]
        
        params = {
            'q': search_query,
            'format': 'json',
            'categories': 'general',
            'language': 'en'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try each SearXNG instance until one works
        for searxng_url in searxng_instances:
            try:
                print(f"Trying SearXNG instance: {searxng_url}")
                response = requests.get(searxng_url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    print(f"✓ Success! Found {len(results)} results from {searxng_url}")
                    
                    if results:
                        flight_info = []
                        
                        for idx, result in enumerate(results[:5], 1):
                            title = result.get('title', 'No title')
                            url = result.get('url', '')
                            content = result.get('content', '')
                            
                            flight_info.append({
                                'title': title,
                                'url': url,
                                'snippet': content
                            })
                        
                        response_text = f"""
⚠️ **Note: The live flight booking API is temporarily unavailable.**

🔍 **Here's what I found from web search for "{search_query}":**

"""
                        for idx, info in enumerate(flight_info, 1):
                            snippet = info['snippet'][:200] if info['snippet'] else "No description available"
                            response_text += f"""
**{idx}. {info['title']}**
{snippet}...
🔗 {info['url']}

"""
                        
                        response_text += """
💡 **Recommendations:**
- Visit the links above for real-time pricing and availability
- Check airline websites directly for best deals
- Compare prices on multiple booking platforms
- The live API should be back online soon - try again later!

⚠️ **Disclaimer:** The information above is from web search results and may not reflect current prices or availability. These are estimated options found on the internet.
"""
                        
                        return {"response": response_text}
                    
            except Exception as e:
                print(f"✗ Failed with {searxng_url}: {str(e)}")
                continue  # Try next instance
        
        # If all SearXNG instances fail, try DuckDuckGo as final fallback
        print("All SearXNG instances failed, trying DuckDuckGo HTML search...")
        try:
            ddg_url = "https://html.duckduckgo.com/html/"
            ddg_data = {
                'q': search_query
            }
            ddg_response = requests.post(ddg_url, data=ddg_data, headers=headers, timeout=10)
            
            if ddg_response.status_code == 200:
                print("✓ DuckDuckGo search successful")
                
                soup = BeautifulSoup(ddg_response.text, 'html.parser')
                results = soup.find_all('div', class_='result__body', limit=5)
                
                if results:
                    flight_info = []
                    for result in results:
                        title_elem = result.find('a', class_='result__a')
                        snippet_elem = result.find('a', class_='result__snippet')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                            
                            flight_info.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
                    
                    if flight_info:
                        response_text = f"""
⚠️ **Note: The live flight booking API is temporarily unavailable.**

🔍 **Here's what I found from web search for "{search_query}":**

"""
                        for idx, info in enumerate(flight_info, 1):
                            snippet = info['snippet'][:200] if info['snippet'] else "No description available"
                            response_text += f"""
**{idx}. {info['title']}**
{snippet}...
🔗 {info['url']}

"""
                        
                        response_text += """
💡 **Recommendations:**
- Visit the links above for real-time pricing and availability
- Check airline websites directly for best deals
- Compare prices on multiple booking platforms
- The live API should be back online soon - try again later!

⚠️ **Disclaimer:** The information above is from web search results and may not reflect current prices or availability. These are estimated options found on the internet.
"""
                        
                        return {"response": response_text}
        except Exception as e:
            print(f"✗ DuckDuckGo fallback also failed: {str(e)}")
        
        # If everything fails, return generic fallback
        print("All search methods failed, returning generic fallback")
        return {"response": get_fallback_message(state)}
    
    return {}


def hotel_tool(state: AgentState):
    if state.intent is None: 
        return {"response": "Internal error: missing intent"}
    i = state.intent

    if not i.get("destination"):
        return {"hotels": [], "response": "Missing destination city for hotel search"}
    
    if not i.get("check_in") or not i.get("check_out"):
        return {"hotels": [], "response": "Missing check-in or check-out dates for hotel search"}

    try:
        print(f"\n{'='*70}")
        print("HOTEL SEARCH DEBUG - START")
        print(f"{'='*70}")
        print(f"Step 1: Getting hotels in city: {i['destination']}")
        
        hotels_data = amadeus_service.search_hotels_by_city(i['destination'])
        
        if not hotels_data:
            print(f"❌ No hotels found in city: {i['destination']}")
            return {"hotels": [], "response": f"No hotels found in city: {i['destination']}"}
        
        print(f"✅ Found {len(hotels_data)} hotels in {i['destination']}")
        
        hotelIds = [hotel['hotelId'] for hotel in hotels_data[:30] if 'hotelId' in hotel]
        
        if not hotelIds:
            print("❌ Could not extract hotel IDs")
            return {"hotels": [], "response": "Could not extract hotel IDs"}
        
        print(f"Step 2: Searching offers for {len(hotelIds)} hotel IDs")
        print(f"{'='*70}\n")
        
        valid_offers = []
        
        for hotel_id in hotelIds:
            try:
                offer_data = amadeus_service.search_hotel_offers(
                    hotel_id,
                    i['travelers'],
                    i['check_in'],
                    i['check_out']
                )
                if offer_data:
                    valid_offers.extend(offer_data)
                    print(f"  ✓ Found offers for {hotel_id}")
                    
                    if len(valid_offers) >= 5:
                        break
            except ResponseError as e:
                error_code = str(e)
                if "429" in error_code:
                    print("  ⏸️  Rate limited, waiting...")
                    import time
                    time.sleep(0.5)
                else:
                    print(f"  ✗ Skipping {hotel_id}: {error_code}")
                continue
        
        if valid_offers:
            print(f"\n✅ Successfully found {len(valid_offers)} hotel offers")
            print(f"{'='*70}\n")
            return {"hotels": valid_offers}
        else:
            # Fallback: return basic hotel info without offers
            print("\n⚠️  No offers found, returning basic hotel information")
            print(f"{'='*70}\n")
            basic_hotels = []
            for hotel in hotels_data[:5]:
                basic_hotels.append({
                    "hotel": hotel,
                    "available": False,
                    "offers": []
                })
            
            if basic_hotels:
                return {
                    "hotels": basic_hotels,
                    "response": f"Found {len(basic_hotels)} hotels in {i['destination']}, but no pricing/availability for your dates. Here are the hotels:"
                }
            else:
                return {"hotels": [], "response": f"No available hotel offers in {i['destination']} for {i['check_in']} to {i['check_out']}."}
            
    except ResponseError as e:
        error_msg = str(e)
        print(f"\n❌ Amadeus ResponseError: {error_msg}")
        print(f"{'='*70}\n")
        return {"hotels": [], "response": f"Hotel search error: {error_msg}"}
    except Exception as e:
        print("\n❌ UNEXPECTED ERROR")
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n")
        return {"hotels": [], "response": f"Unexpected hotel error: {str(e)}"}


def clarify_node(state: AgentState):
    """Provide helpful clarification when information is missing"""
    
    intent_data = state.intent or {}
    reasoning = intent_data.get("reasoning", "")
    
    # Build response based on what's missing
    response = "I need more information to help you book your travel.\n\n"
    
    if reasoning:
        response += f"**{reasoning}**\n\n"
    
    # Get all available info
    origin = intent_data.get("origin")
    destination = intent_data.get("destination")
    check_in = intent_data.get("check_in")
    check_out = intent_data.get("check_out")
    
    # Show what we have
    has_info = []
    if origin:
        has_info.append(f"✓ Departure: {origin}")
    if destination:
        has_info.append(f"✓ Destination: {destination}")
    if check_in:
        has_info.append(f"✓ Check-in/Departure date: {check_in}")
    if check_out:
        has_info.append(f"✓ Check-out date: {check_out}")
    
    if has_info:
        response += "**What I have:**\n"
        for item in has_info:
            response += f"{item}\n"
        response += "\n"
    
    # Provide context-specific help
    if origin and not destination:
        response += "**What I need:**\n"
        response += "• Destination/Arrival city (e.g., Delhi, Bangalore, Chennai)\n"
        if not check_in:
            response += "• Travel/Departure date (e.g., tomorrow, 25th January)\n"
        response += "\n**Example:** 'to Delhi on 25th January'\n"
    
    elif destination and not origin:
        response += "**What I need:**\n"
        response += "• Departure city (e.g., Mumbai, Bangalore)\n"
        if not check_in:
            response += "• Travel date (e.g., tomorrow, 25th January)\n"
        response += "\n**Example:** 'from Mumbai on 25th January'\n"
    
    else:
        # Generic help
        response += "**For flight bookings, I need:**\n"
        response += "• Departure city (e.g., Mumbai, BOM)\n"
        response += "• Arrival city (e.g., Delhi, DEL)\n"
        response += "• Travel date (e.g., tomorrow, 25th January)\n\n"
        
        response += "**For hotel bookings, I need:**\n"
        response += "• Destination city (e.g., Delhi, Mumbai)\n"
        response += "• Check-in date (e.g., 25th January)\n"
        response += "• Check-out date (e.g., 27th January, or '3 nights')\n\n"
        
        response += "**Examples:**\n"
        response += "• 'Book a flight from Mumbai to Delhi on 25th January'\n"
        response += "• 'Book a hotel in Delhi from 25th to 27th January'\n"
        response += "• 'Flight and hotel to Bangalore next week for 3 nights'\n"
    
    return {"response": response}

def synthesis_node(state: AgentState):
    lines = []
    
    # Handle flights
    if state.flights:
        lines.append("✈️ **FLIGHTS:**")
        for f in state.flights[:5]:
            segment = f["itineraries"][0]["segments"][0]
            flight_code = f"{segment['carrierCode']} {segment['number']}"
            
            dt = datetime.fromisoformat(segment["departure"]["at"])
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None) 
            time_str = dt.strftime("%d %b %Y, %I:%M %p")

            price_eur = float(f["price"]["total"])
            price_inr = int(price_eur * EUR_TO_INR)

            dep_code = segment["departure"]["iataCode"]
            arr_code = segment["arrival"]["iataCode"]

            dep_city = airport_cache.get_city_name(dep_code)
            arr_city = airport_cache.get_city_name(arr_code)

            route_str = f"{dep_city} ({dep_code}) → {arr_city} ({arr_code})"

            lines.append(
                f"  {flight_code} | {route_str} | {time_str} | ₹{price_inr}"
            )
        lines.append("")
    
    # Handle hotels
    if state.hotels:
        lines.append("🏨 **HOTELS:**")
        lines.append("")
        
        for idx, h in enumerate(state.hotels[:5], 1):
            hotel_info = h.get('hotel', {})
            hotel_name = hotel_info.get('name', 'Unknown Hotel')
            hotel_id = hotel_info.get('hotelId', 'N/A')
            
            lines.append(f"{idx}. **{hotel_name}** (ID: {hotel_id})")
            
            offers = h.get('offers', [])
            if offers:
                offer = offers[0]
                
                price_info = offer.get('price', {})
                currency = price_info.get('currency', 'EUR')
                total = float(price_info.get('total', 0))
                base = float(price_info.get('base', 0))
                
                if currency == 'EUR':
                    price_inr = int(total * EUR_TO_INR)
                    base_inr = int(base * EUR_TO_INR)
                elif currency == 'GBP':
                    price_inr = int(total * 125)
                    base_inr = int(base * 125)
                elif currency == 'USD':
                    price_inr = int(total * 83)
                    base_inr = int(base * 83)
                else:
                    price_inr = int(total)
                    base_inr = int(base)
                
                lines.append(f"   💰 Price: ₹{price_inr} total (Base: ₹{base_inr}) | Currency: {currency}")
                
                room_info = offer.get('room', {})
                room_estimated = room_info.get('typeEstimated', {})
                room_category = room_estimated.get('category', 'Standard Room').replace('_', ' ').title()
                beds = room_estimated.get('beds', 'N/A')
                bed_type = room_estimated.get('bedType', 'N/A')
                
                lines.append(f"   🛏️  Room: {room_category} | {beds} bed(s) - {bed_type}")
                
                room_desc = room_info.get('description', {})
                desc_text = room_desc.get('text', '')
                if desc_text:
                    desc_short = desc_text[:150] + '...' if len(desc_text) > 150 else desc_text
                    lines.append(f"   📝 {desc_short}")
                
                check_in = offer.get('checkInDate', 'N/A')
                check_out = offer.get('checkOutDate', 'N/A')
                lines.append(f"   📅 {check_in} to {check_out}")
                
                policies = offer.get('policies', {})
                payment_type = policies.get('paymentType', 'N/A')
                cancellation = policies.get('cancellation', {})
                cancel_type = cancellation.get('type', 'N/A')
                cancel_desc = cancellation.get('description', {})
                if isinstance(cancel_desc, dict):
                    cancel_desc_text = cancel_desc.get('text', 'No cancellation info')
                else:
                    cancel_desc_text = str(cancel_desc) if cancel_desc else 'No cancellation info'
                
                lines.append(f"   🏷️  Payment: {payment_type} | Cancellation: {cancel_type}")
                lines.append(f"   ℹ️  {cancel_desc_text}")
            else:
                lines.append("   ℹ️  No pricing available for selected dates")
                
                address = hotel_info.get('address', {})
                city_name = address.get('cityName', '')
                if city_name:
                    lines.append(f"   📍 Location: {city_name}")
                
                distance = hotel_info.get('distance', {})
                if distance:
                    dist_value = distance.get('value', '')
                    dist_unit = distance.get('unit', '')
                    if dist_value:
                        lines.append(f"   📏 Distance from center: {dist_value} {dist_unit}")
                
            lines.append("")
    
    if not lines:
        return {"response": "No results available for your search."}
    
    return {"response": "\n".join(lines)}