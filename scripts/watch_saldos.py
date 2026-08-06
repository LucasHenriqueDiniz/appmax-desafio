"""Painel ao vivo dos saldos: tabela colorida que atualiza a cada segundo.

Deixe rodando num terminal enquanto dispara transferencias no outro e
veja os saldos mudando em tempo real (mudancas ficam destacadas).

Uso:
    docker compose up -d
    uv run python scripts/watch_saldos.py
"""

import os
import time
from decimal import Decimal

from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg://appmax:appmax@localhost:5432/appmax"
REFRESH_SECONDS = 1.0
HIGHLIGHT_CYCLES = 4  # por quantos refreshes uma mudanca fica destacada

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
CYAN = "\x1b[36m"

BALANCES_QUERY = """
    SELECT u.id, u.full_name, u.type, w.balance
    FROM users u JOIN wallets w ON w.user_id = u.id
    ORDER BY u.id
"""

TRANSFERS_QUERY = """
    SELECT to_char(created_at, 'HH24:MI:SS') AS hora,
           payer_id, payee_id, amount, notification_status
    FROM transfers ORDER BY created_at DESC LIMIT 5
"""


def render(rows, transfers, highlights) -> list[str]:
    lines = []
    refresh = f"{DIM}(atualiza a cada {REFRESH_SECONDS:.0f}s){RESET}"
    lines.append(f"{BOLD}  SALDOS AO VIVO{RESET} {refresh}")
    lines.append("")

    total = Decimal("0")
    for user_id, name, user_type, balance in rows:
        total += balance
        tag = f"{CYAN}[lojista]{RESET}" if user_type == "merchant" else f"{DIM}[comum]  {RESET}"
        line = f"    {tag} #{user_id:<3} {name:<20} R$ {balance:>10}"
        if user_id in highlights:
            old = highlights[user_id][0]
            delta = balance - old
            signal = "+" if delta > 0 else ""
            line += f"  {BOLD}{YELLOW}<- mudou! ({signal}{delta}){RESET}"
        lines.append(line)

    lines.append("")
    lines.append(f"    {GREEN}{BOLD}soma de todos os saldos: R$ {total:>10}{RESET}"
                 f"  {DIM}<- nunca muda{RESET}")
    lines.append("")
    lines.append(f"{BOLD}  ULTIMAS TRANSFERENCIAS{RESET}")

    if not transfers:
        lines.append(f"    {DIM}(nenhuma ainda){RESET}")
    for hora, payer_id, payee_id, amount, notification in transfers:
        color = {"sent": GREEN, "failed": RED, "pending": YELLOW}.get(notification, DIM)
        lines.append(
            f"    {DIM}{hora}{RESET}  #{payer_id} -> #{payee_id}  R$ {amount:>8}"
            f"  {color}{notification}{RESET}"
        )
    return lines


def main() -> None:
    os.system("")  # habilita ANSI no console classico do Windows
    engine = create_engine(DB_URL)
    previous: dict[int, Decimal] = {}
    highlights: dict[int, tuple[Decimal, int]] = {}  # user_id -> (saldo antigo, ciclos restantes)

    while True:
        with engine.connect() as connection:
            rows = connection.execute(text(BALANCES_QUERY)).all()
            transfers = connection.execute(text(TRANSFERS_QUERY)).all()

        for user_id, _, _, balance in rows:
            if user_id in previous and previous[user_id] != balance:
                highlights[user_id] = (previous[user_id], HIGHLIGHT_CYCLES)
            previous[user_id] = balance
        highlights = {
            uid: (old, cycles - 1) for uid, (old, cycles) in highlights.items() if cycles > 0
        }

        # home + limpa cada linha: menos flicker que limpar a tela inteira
        lines = render(rows, transfers, highlights)
        frame = "\x1b[H" + "\n".join(f"\x1b[K{line}" for line in lines)
        print(frame + "\x1b[J", flush=True)

        if os.environ.get("WATCH_ONCE"):  # para testes: renderiza 1 frame e sai
            break
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
