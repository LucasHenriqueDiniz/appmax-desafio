import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_serializer


class TransferRequest(BaseModel):
    """Contrato obrigatorio do enunciado: {"value": 100.0, "payer": 4, "payee": 15}.

    value vira Decimal ja na borda (Pydantic converte via string — o float
    do JSON nunca contamina o calculo). decimal_places=2 recusa fracoes
    de centavo como 0.001.
    """

    value: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    # limitados ao range do INTEGER do Postgres: id fora do range vira 422
    # na borda em vez de estourar no driver como 500
    payer: Annotated[int, Field(ge=1, le=2_147_483_647)]
    payee: Annotated[int, Field(ge=1, le=2_147_483_647)]


class TransferResponse(BaseModel):
    id: uuid.UUID
    value: Decimal
    payer: int
    payee: int
    status: str
    notification_status: str
    created_at: datetime

    @field_serializer("value")
    def serialize_value(self, value: Decimal) -> str:
        # dinheiro sempre com 2 casas na resposta ("100.00", nunca "100.0")
        return f"{value:.2f}"


class ErrorResponse(BaseModel):
    code: str
    message: str
