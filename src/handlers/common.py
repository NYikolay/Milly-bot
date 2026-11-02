from html import escape as html_escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle the ``/start`` command.

    Purpose:
        Sends a greeting that includes the user's escaped full name.

    Args:
        message: Incoming message that triggered the command.

    Notes:
        - The name is HTML-escaped for the default HTML parse mode.
        - Falls back to ``"друг"`` when ``from_user`` is missing.
    """
    name = html_escape(message.from_user.full_name) if message.from_user else "друг"
    await message.answer(f"Привет, {name}! Я на связи.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Handle the ``/help`` command.

    Purpose:
        Sends the static help text listing available commands.

    Args:
        message: Incoming message that triggered the command.
    """
    await message.answer(
        "Это скелет бота Milly.\n\nДоступные команды:\n/start — запуск\n/help — помощь",
    )
