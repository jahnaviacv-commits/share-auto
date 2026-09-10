from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.corridor import Corridor, Station
from app.models.vehicle import Vehicle, VehicleStatus
from app.schemas import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

@router.post("/message", response_model=ChatMessageResponse)
async def process_chat_message(req: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    msg = req.message.lower()

    if "dlf" in msg or "hitec" in msg or "which auto" in msg or "route" in msg:
        return ChatMessageResponse(
            response="You can take Route H1 Express directly from HITEC City Metro Stand 2. Multiple active autos are approaching right now!",
            suggestions=[
                "Book a seat on AUTO-HYD-903",
                "How do 5-seater vs 9-seater fares compare?",
                "Where is the nearest stand at Mindspace?"
            ],
            card_data={
                "autos": [
                    {
                        "code": "AUTO-HYD-903",
                        "type": "9-Seater Maxi",
                        "eta": "Departing in 4 mins",
                        "fare": 25.0,
                        "available_seats": 4,
                        "badge": "Fixed Fare Guarantee"
                    },
                    {
                        "code": "AUTO-HYD-501",
                        "type": "5-Seater Rapid Pod",
                        "eta": "Departing in 2 mins",
                        "fare": 30.0,
                        "available_seats": 1,
                        "badge": "Point-to-Point Express"
                    }
                ]
            }
        )
    elif "5-seater" in msg or "9-seater" in msg or "compare" in msg or "fare" in msg or "price" in msg:
        return ChatMessageResponse(
            response=(
                "Here is how our corridor fares break down:\n\n"
                "• 9-Seater Maxi (e.g. Bajaj Maxima): Fixed ₹25 corridor fare. 3 benches, high legroom, rear luggage rack.\n"
                "• 5-Seater Pod (e.g. Piaggio Ape): Fixed ₹30 corridor fare. Quicker point-to-point drop with fewer intermediate stops.\n\n"
                "Both options are covered by ZeroOne Fixed Fare guarantee (zero surge pricing)."
            ),
            suggestions=[
                "Which auto goes from HITEC Metro to DLF?",
                "Help me book a seat on Route H1"
            ]
        )
    elif "mindspace" in msg or "stand" in msg or "stop" in msg:
        return ChatMessageResponse(
            response=(
                "The nearest ZeroOne Shared-Auto stand at Mindspace is at Mindspace Main Gate 1 (Flyover Pillar 24).\n"
                "Three Route H1 autos are currently holding at this stand. Next departure in ~2 minutes."
            ),
            suggestions=[
                "Which auto goes from HITEC Metro to DLF?",
                "Emergency 112 assistance"
            ]
        )
    elif "sos" in msg or "emergency" in msg or "help" in msg or "police" in msg:
        return ChatMessageResponse(
            response=(
                "EMERGENCY ASSISTANCE INITIATED. Your GPS location has been beamed to the "
                "Hyderabad Transit Police Desk and ZeroOne Safety Operations. Direct Emergency Line: 112."
            ),
            suggestions=[
                "Call Emergency Line 112",
                "Contact Fleet Controller Desk"
            ]
        )
    else:
        return ChatMessageResponse(
            response=(
                "I found multiple active shared-autos along your corridor. Route H1 runs every 2-3 minutes "
                "between HITEC Metro and DLF Cybercity. Would you like me to reserve a seat on the next departing vehicle?"
            ),
            suggestions=[
                "Which auto goes from HITEC Metro to DLF?",
                "How do 5-seater vs 9-seater fares compare?",
                "Where is the nearest ShareAuto stand at Mindspace?"
            ]
        )
