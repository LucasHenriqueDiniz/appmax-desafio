from fastapi import APIRouter, Request, status

from app.api.schemas import ErrorResponse, TransferRequest, TransferResponse
from app.application.transfer_service import TransferService

router = APIRouter()


@router.post(
    "/transfer",
    status_code=status.HTTP_201_CREATED,
    response_model=TransferResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Negada pelo autorizador externo"},
        404: {"model": ErrorResponse, "description": "Pagador ou beneficiario inexistente"},
        409: {"model": ErrorResponse, "description": "Saldo insuficiente"},
        422: {"model": ErrorResponse, "description": "Valor invalido ou regra de negocio violada"},
        503: {"model": ErrorResponse, "description": "Autorizador externo indisponivel"},
    },
)
def create_transfer(payload: TransferRequest, request: Request) -> TransferResponse:
    service: TransferService = request.app.state.transfer_service
    result = service.execute(value=payload.value, payer_id=payload.payer, payee_id=payload.payee)
    return TransferResponse(
        id=result.id,
        value=result.value,
        payer=result.payer,
        payee=result.payee,
        status=result.status,
        notification_status=result.notification_status,
        created_at=result.created_at,
    )
