from fastapi import APIRouter, Depends
from rabbitmq import publish_order
from schemas.orders import OrderCreate, OrderOut

from shared.database import get_session
from shared.logger import get_logger
from shared.models import Order

logger = get_logger(__name__)

router = APIRouter(
    prefix="/orders",
)

session_dep = Depends(get_session)

@router.post("/", response_model=OrderOut)
async def create_order(
    order: OrderCreate,
    session: session_dep
):
    new_order = Order(item=order.item, qty=order.qty)
    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)
    await publish_order(new_order.id)

    logger.info(f"Order created with ID: {new_order.id}")
    return new_order
