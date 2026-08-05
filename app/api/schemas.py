import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    """Contrato obrigatorio do enunciado: {"value": 100.0, "payer": 4, "payee": 15}.

    value vira Decimal ja na borda (Pydantic converte via string — o float
    do JSON nunca contamina o calculo). decimal_places=2 recusa fracoes
    de centavo como 0.001.
    """

    value: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    payer: int
    payee: int


class TransferResponse(BaseModel):
    id: uuid.UUID
    value: Decimal
    payer: int
    payee: int
    status: str
    notification_status: str
    created_at: datetime


class ErrorResponse(BaseModel):
    code: str
    message: str
