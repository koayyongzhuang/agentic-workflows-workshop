"""Pattern 6: Supervisor with tool-owning specialists: the Travel Booking example.

                       ┌─▶ flight_agent      (search / retrieve / change / cancel flight booking)
    user ─▶ supervisor ┼─▶ destination_agent (recommend destination)
       ▲         ▲     └─▶ hotel_agent       (suggest / retrieve / change / cancel hotel booking)
       │         └──── response ◀─┘
       └── final response

This is the "Multi-Agent Orchestration in Action" slide as code. The same
supervisor idea powers the Citizen Services Platform; here the domain is
simpler, so you can focus on the routing loop.

    python -m part2_multi_agent.patterns.supervisor_travel
    python -m part2_multi_agent.patterns.supervisor_travel "Change booking BK-1001 to 2026-12-20 and suggest a hotel in Tokyo"
"""

from __future__ import annotations

import re
import sys
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from part2_multi_agent.patterns.common import console, run_demo
from workshop.agents import Specialist, run_specialist
from workshop.llm import get_chat_model

# ----------------------------------------------------------------------------- mock travel APIs
FLIGHTS = {"BK-1001": {"from": "SIN", "to": "NRT", "date": "2026-12-18", "status": "CONFIRMED"}}
HOTELS = {"HT-2001": {"city": "Tokyo", "hotel": "Shinjuku Garden Hotel", "nights": 4, "status": "CONFIRMED"}}


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search available flights between two cities (IATA codes or names) on a date (YYYY-MM-DD)."""
    return f"3 flights {origin}->{destination} on {date}: SQ638 08:05 $820, JL712 10:40 $760, NH842 22:15 $690"


@tool
def retrieve_flight_booking(booking_id: str) -> str:
    """Retrieve a flight booking by its ID (format BK-1234)."""
    return str(FLIGHTS.get(booking_id, f"No flight booking {booking_id}"))


@tool
def change_flight_booking(booking_id: str, new_date: str) -> str:
    """Change the date of an existing flight booking."""
    if booking_id not in FLIGHTS:
        return f"No flight booking {booking_id}"
    FLIGHTS[booking_id]["date"] = new_date
    return f"Flight {booking_id} moved to {new_date}: {FLIGHTS[booking_id]}"


@tool
def cancel_flight_booking(booking_id: str) -> str:
    """Cancel an existing flight booking."""
    if booking_id in FLIGHTS:
        FLIGHTS[booking_id]["status"] = "CANCELLED"
    return str(FLIGHTS.get(booking_id, f"No flight booking {booking_id}"))


@tool
def suggest_hotels(city: str) -> str:
    """Suggest hotels in a city with nightly prices."""
    return f"Hotels in {city}: Garden Hotel $180/night, Station Inn $120/night, River Ryokan $260/night"


@tool
def retrieve_hotel_booking(booking_id: str) -> str:
    """Retrieve a hotel booking by its ID (format HT-1234)."""
    return str(HOTELS.get(booking_id, f"No hotel booking {booking_id}"))


@tool
def change_hotel_booking(booking_id: str, nights: int) -> str:
    """Change the number of nights of an existing hotel booking."""
    if booking_id not in HOTELS:
        return f"No hotel booking {booking_id}"
    HOTELS[booking_id]["nights"] = nights
    return str(HOTELS[booking_id])


@tool
def cancel_hotel_booking(booking_id: str) -> str:
    """Cancel an existing hotel booking."""
    if booking_id in HOTELS:
        HOTELS[booking_id]["status"] = "CANCELLED"
    return str(HOTELS.get(booking_id, f"No hotel booking {booking_id}"))


@tool
def recommend_destination(preferences: str) -> str:
    """Recommend travel destinations matching the traveller's preferences (season, budget, interests)."""
    return "Recommended: Kyoto (autumn colours, temples), Hokkaido (snow, onsen), Taipei (food, budget-friendly)"


# ----------------------------------------------------------------------------- specialists
SPECIALISTS = {
    "flight_agent": Specialist("flight_agent", "You manage flights. Use your tools; report booking IDs exactly.",
                               [search_flights, retrieve_flight_booking, change_flight_booking, cancel_flight_booking], governed=False),
    "hotel_agent": Specialist("hotel_agent", "You manage hotels. Use your tools; report booking IDs exactly.",
                              [suggest_hotels, retrieve_hotel_booking, change_hotel_booking, cancel_hotel_booking], governed=False),
    "destination_agent": Specialist("destination_agent", "You recommend destinations using your tool.",
                                    [recommend_destination], governed=False),
}


class TravelRoute(BaseModel):
    next: Literal["flight_agent", "hotel_agent", "destination_agent", "FINISH"]
    task: str = Field(description="Instruction for that agent")

    @classmethod
    def mock_response(cls, text: str) -> "TravelRoute":  # offline mock only
        req = re.search(r"User request:\s*(.*)", text)
        done = re.search(r"Done:\s*(.*)", text)
        r, d = (req.group(1).lower() if req else text.lower()), (done.group(1) if done else "")
        for agent, words in (("flight_agent", ("flight", "fly", "bk-")), ("hotel_agent", ("hotel", "ht-", "stay")),
                             ("destination_agent", ("recommend", "where", "destination", "suggest a place"))):
            if any(w in r for w in words) and agent not in d:
                return cls(next=agent, task=req.group(1) if req else r)
        return cls(next="FINISH", task="")


class TravelState(MessagesState):
    done: list[str]
    next: str
    task: str
    reports: str


def supervisor(state: TravelState, config: RunnableConfig) -> dict:
    request = next(m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage))
    llm = get_chat_model(role="travel_supervisor").with_structured_output(TravelRoute)
    route = llm.invoke([
        SystemMessage("You are a travel supervisor. Route to flight_agent, hotel_agent or destination_agent; "
                      "each at most once. FINISH when the request is fully handled."),
        HumanMessage(f"User request: {request}\nDone: {', '.join(state.get('done', [])) or 'none'}\n"
                     f"Reports:\n{state.get('reports', '')}"),
    ], config)
    if route.next in state.get("done", []):
        route = TravelRoute(next="FINISH", task="")
    return {"next": route.next, "task": route.task}


def make_worker(name: str):
    def worker(state: TravelState, config: RunnableConfig) -> dict:
        res = run_specialist(SPECIALISTS[name], [HumanMessage(state["task"])], config)
        return {"done": [*state.get("done", []), name], "reports": state.get("reports", "") + f"\n[{name}] {res.report.content}",
                "messages": [res.report]}  # the "Response" arrow back to the supervisor
    return worker


def final_response(state: TravelState, config: RunnableConfig) -> dict:
    return {"messages": [AIMessage(state.get("reports", "").strip() or "Nothing to do.", name="supervisor")]}


def build_graph():
    g = StateGraph(TravelState)
    g.add_node("supervisor", supervisor)
    for name in SPECIALISTS:
        g.add_node(name, make_worker(name))
        g.add_edge(name, "supervisor")
    g.add_node("final_response", final_response)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", lambda s: s["next"] if s["next"] in SPECIALISTS else "final_response",
                            [*SPECIALISTS, "final_response"])
    g.add_edge("final_response", END)
    return g.compile(name="travel_supervisor")


def main() -> None:
    request = " ".join(sys.argv[1:]) or "Change my flight BK-1001 to 2026-12-20 and suggest hotels in Tokyo."
    result = run_demo("supervisor_travel", build_graph(), {"messages": [HumanMessage(request)]}, "reports")
    console.print(f"[dim]agents used: {' → '.join(result.get('done', []))}[/]")


if __name__ == "__main__":
    main()
