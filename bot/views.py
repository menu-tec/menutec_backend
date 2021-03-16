import json
from hashlib import sha256

from django.conf import settings as conf
from django.http import HttpResponseForbidden, HttpResponse
from telegram import Update

from bot.bot_controller import BotController

dispatcher = BotController().dispatcher


def webhook(request, secret: str):
    if not _verify_secret(secret):
        return HttpResponseForbidden("Access not allowed")

    update = Update.de_json(json.loads(request.body.decode()), dispatcher.bot)

    dispatcher.process_update(update)

    return HttpResponse("Ok")


def _verify_secret(secret: str) -> bool:
    s = sha256()
    s.update(conf.BOT["WEBHOOK_SECRET"].encode("utf-8"))

    return secret.lower() == s.hexdigest().lower()
