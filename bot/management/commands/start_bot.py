import logging

from django.core.management.base import BaseCommand

from bot.bot_controller import BotController

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        BotController().run()
