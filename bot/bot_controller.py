import datetime
from queue import Queue
from threading import Thread

from telegram import *
from telegram.ext import *
from django.conf import settings as conf

from bot import telegramcalendar

MENUS = "Menús"
MAKE_MENU = "Crear menú"
LIST_MENUS = "Ver próximos menús"
DELETE_MENU = "Eliminar menú"

MENU_TYPES = {
    "DESAYUNO": "Desayuno (08:00 - 10:00)",
    "ALMUERZO": "Almuerzo (11:00 - 14:00)",
    "CAFE": "Café (15:00 - 16:00)",
    "CENA": "Cena (17:00 - 19:30)",
}

(
    SELECTING_MENU_DATE,
    SELECTING_MENU_TYPE,
    ADDING_MENU_ELEMENTS,
    SELECTING_MEAL_NAME,
    SELECTING_MEAL_PRICE,

) = range(5)

MENU_TYPE_CHOICE = 6
MENU_DATE_CHOICE = 7
MENU_MEALS = "meals"
MENU_TEMP_MEAL = "tmp_meal"
MENU_NEW_MEAL = "NEW_MEAL"
MENU_END_ADDING_MEAL = "END_MEALS"

CHOOSE_DATE_TO_DELETE = "date_to_delete"
CHOOSE_TYPE_TO_DELETE = "type_to_delete"

CREATED_MENUS = {}


class BotController:

    def __init__(self):
        self.updater = Updater(conf.BOT['TOKEN'])
        self.dispatcher = Dispatcher(Bot(conf.BOT['TOKEN']), None, workers=0)
        self._init_handlers()
        # self.update_queue = Queue()
        # self.dispatcher = Dispatcher(Bot(token), self.update_queue)

    # def get_queue(self) -> Queue:
    #
    #     # Start the thread
    #     thread = Thread(target=self.dispatcher.start, name='dispatcher')
    #     thread.start()
    #
    #     return self.update_queue

    def run(self) -> None:
        self._init_handlers()

        self.updater.start_polling()

        self.updater.idle()

    def _unknown_command(self, update: Update, _: CallbackContext) -> None:
        update.message.reply_text(
            "Opción no reconocida, intente haciendo click aquí /start para ver el menú de comandos",
        )

    def _start(self, update: Update, context: CallbackContext) -> None:
        # update.message.reply_text(
        #     f"Group id: {update.message.chat.id}\nUser id: {context.bot.get_chat_member(-1001439515681, update.message.from_user.id).custom_title}"
        # )

        options = [
            [MENUS]
        ]

        kb = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)

        update.message.reply_text(
            "Hola, seleccione una opción del menú para continuar.",
            reply_markup=kb,
        )

    def _menus(self, update: Update, _: CallbackContext) -> None:
        options = [
            [LIST_MENUS, MAKE_MENU],
            ["Editar menú", DELETE_MENU]
        ]

        kb = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)

        update.message.reply_text(
            "Muy bien, que desea hacer?.",
            reply_markup=kb,
        )

    def _make_menu(self, update: Update, _: CallbackContext) -> int:

        update.message.reply_text(
            "Seleccione la fecha del nuevo menú"
            "\nPuede escribir /cancel en cualquier momento para cancelar la creación del menú",
            reply_markup=telegramcalendar.create_calendar()
        )

        return SELECTING_MENU_DATE

    def _process_menu_type(self, update: Update, context: CallbackContext) -> int:
        context.user_data[MENU_TYPE_CHOICE] = update.callback_query.data

        context.user_data[MENU_MEALS] = {}

        update.callback_query.edit_message_text(
            text=f"El menú de {MENU_TYPES.get(update.callback_query.data)} "
                 f"para la fecha {context.user_data[MENU_DATE_CHOICE]} no tiene entradas. "
                 f"Presione el siguiente botón para crear una entrada nueva",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Añadir nueva entrada", callback_data=MENU_NEW_MEAL)]])
        )

        return ADDING_MENU_ELEMENTS

    def _add_meal(self, update: Update, context: CallbackContext):
        context.user_data[MENU_TEMP_MEAL] = update.message.text

        update.message.reply_text(
            f"Escriba el precio de '{update.message.text}'",
        )

        return SELECTING_MEAL_PRICE

    def _add_meal_price(self, update: Update, context: CallbackContext):
        context.user_data[MENU_MEALS][context.user_data[MENU_TEMP_MEAL]] = update.message.text

        update.message.reply_text(
            f"El menú de {MENU_TYPES.get(context.user_data.get(MENU_TYPE_CHOICE))} " +
            f"para la fecha {context.user_data[MENU_DATE_CHOICE]} tiene las siguientes entradas:\n\n" +
            "{}".format("\n".join([f"{p} {n}" for n, p in context.user_data[MENU_MEALS].items()])) +
            "\n\n¿Desea agregar otra entrada?",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Añadir nueva entrada", callback_data=MENU_NEW_MEAL)],
                 [InlineKeyboardButton(text="Crear menú", callback_data=MENU_END_ADDING_MEAL)]])
        )

        return ADDING_MENU_ELEMENTS

    def _process_adding_meal(self, update: Update, context: CallbackContext):
        if update.callback_query.data == MENU_NEW_MEAL:

            update.callback_query.edit_message_text(
                text="Escriba el nombre de la nueva entrada"
            )
            return SELECTING_MEAL_NAME

        elif update.callback_query.data == MENU_END_ADDING_MEAL:

            if not CREATED_MENUS.get(context.user_data[MENU_DATE_CHOICE]):
                CREATED_MENUS[context.user_data[MENU_DATE_CHOICE]] = {}

            CREATED_MENUS[context.user_data[MENU_DATE_CHOICE]][context.user_data[MENU_TYPE_CHOICE]] = context.user_data[MENU_MEALS]

            print(CREATED_MENUS)

            update.callback_query.edit_message_text(
                text="Menú guardado"
            )
            return ConversationHandler.END


    def _process_menu_date(self, update: Update, context: CallbackContext) -> int:
        selected, date_result = telegramcalendar.process_calendar_selection(context.bot, update)

        if selected:

            if date_result.date() < datetime.date.today():
                update.callback_query.answer(
                    text="No puede crear un menú para una fecha anterior a la actual. "
                         "Por favor escoja una fecha igual o posterior a la fecha de hoy.",
                    show_alert=True
                )

                update.callback_query.edit_message_text(
                    text="Seleccione la fecha del nuevo menú",
                    reply_markup=telegramcalendar.create_calendar()
                )
                return SELECTING_MENU_DATE

            context.user_data[MENU_DATE_CHOICE] = date_result.strftime("%d/%m/%Y")

            if len(CREATED_MENUS) > 0 and CREATED_MENUS.get(context.user_data[MENU_DATE_CHOICE]):
                buttons = [[InlineKeyboardButton(value, callback_data=key)]
                           for key, value in MENU_TYPES.items()
                           if key not in CREATED_MENUS.get(context.user_data[MENU_DATE_CHOICE]).keys()]
            else:
                buttons = [[InlineKeyboardButton(value, callback_data=key)]
                           for key, value in MENU_TYPES.items()]

            if len(buttons) == 0:
                update.callback_query.edit_message_text(
                    text=f"Para esta fecha ya no se puede crear más menús, "
                         f"por favor edite uno existente o elimínelo para crear uno nuevo.",
                )
                return ConversationHandler.END

            update.callback_query.edit_message_text(
                text=f"En qué momento se servirá el menú del día {date_result.strftime('%d/%m/%Y')}?",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            return SELECTING_MENU_TYPE

        return SELECTING_MENU_DATE

    def _list_menus(self, update: Update, _: CallbackContext):

        if len(CREATED_MENUS) == 0:
            update.message.reply_text(
                """
                No hay menús disponibles
                """
            )
            return

        for fecha, menu in CREATED_MENUS.items():
            update.message.reply_text(
                """
                El menú para el día {fecha} es el siguiente:\n\n{entradas}
                """
                    .format(
                    fecha=fecha,
                    entradas="\n\n"
                        .join([
                        "{tipo}:\n{meals}".format(tipo=MENU_TYPES.get(tipo), meals="\n".join([f"{p} {n}" for n, p in meals.items()]))
                        for tipo, meals in menu.items()
                    ])
                )
            )

    def _delete_menu(self, update: Update, _: CallbackContext):

        if len(CREATED_MENUS) == 0:
            update.message.reply_text(
                """
                No hay menús disponibles
                """
            )
            return ConversationHandler.END

        kb = [[InlineKeyboardButton(d, callback_data=f"DATE_DELETE,{d}")] for d in CREATED_MENUS.keys()]

        update.message.reply_text(
            "Escoja la fecha del menú a eliminar:"
            "\nPuede escribir /cancel en cualquier momento para cancelar la eliminación del menú",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        return CHOOSE_DATE_TO_DELETE

    def _process_date_delete(self, update: Update, _: CallbackContext):
        key = update.callback_query.data.split(",")[1]

        kb = [[InlineKeyboardButton(MENU_TYPES.get(d), callback_data=f"TYPE_DELETE,{key},{d}")] for d in CREATED_MENUS.get(key).keys()]

        update.callback_query.edit_message_text(
            text=f"Escoja el tipo de menú a eliminar para el día {key}",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        return CHOOSE_TYPE_TO_DELETE

    def _process_type_delete(self, update: Update, _: CallbackContext):
        key, tipo = update.callback_query.data.split(",")[1:]

        CREATED_MENUS.get(key).pop(tipo)

        if len(CREATED_MENUS.get(key)) == 0:
            CREATED_MENUS.pop(key)

        update.callback_query.edit_message_text(
            text=f"Menú eliminado"
        )

        return ConversationHandler.END

    def _cancel(self, update: Update, _: CallbackContext):

        # for k, v in CREATED_MENUS.items():
        #     if len(v) == 0:
        #         CREATED_MENUS.pop(k)

        update.message.reply_text(
            """
            Operación cancelada
            """
        )

        return ConversationHandler.END

    def _init_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self._start))

        self.dispatcher.add_handler(MessageHandler(Filters.regex(f"^{MENUS}$"), self._menus))

        self.dispatcher.add_handler(MessageHandler(Filters.regex(f"^{LIST_MENUS}$"), self._list_menus))

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[MessageHandler(Filters.regex(f"^{MAKE_MENU}$"), self._make_menu)],
            states={
                SELECTING_MENU_DATE: [
                    CallbackQueryHandler(self._process_menu_date,
                                         pattern=f"^"
                                                 f"(PREV-MONTH.*)|"
                                                 f"(NEXT-MONTH.*)|"
                                                 f"(DAY.*)"
                                                 f"$")
                ],
                SELECTING_MENU_TYPE: [
                    CallbackQueryHandler(self._process_menu_type,
                                         pattern=f"^"
                                                 f"({list(MENU_TYPES.keys())[0]})|"
                                                 f"({list(MENU_TYPES.keys())[1]})|"
                                                 f"({list(MENU_TYPES.keys())[2]})|"
                                                 f"({list(MENU_TYPES.keys())[3]})"
                                                 f"$")
                ],
                ADDING_MENU_ELEMENTS: [
                    CallbackQueryHandler(self._process_adding_meal, pattern=f"^({MENU_NEW_MEAL})|({MENU_END_ADDING_MEAL})$")
                ],
                SELECTING_MEAL_NAME: [
                    MessageHandler(Filters.text, self._add_meal),
                ],
                SELECTING_MEAL_PRICE: [
                    MessageHandler(Filters.regex("[0-9]"), self._add_meal_price),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[MessageHandler(Filters.regex(f"^{DELETE_MENU}$"), self._delete_menu)],
            states={
                CHOOSE_DATE_TO_DELETE: [
                    CallbackQueryHandler(self._process_date_delete,
                                         pattern=f"^"
                                                 f"(DATE_DELETE.*)"
                                                 f"$")
                ],
                CHOOSE_TYPE_TO_DELETE: [
                    CallbackQueryHandler(self._process_type_delete,
                                         pattern=f"^"
                                                 f"(TYPE_DELETE.*)"
                                                 f"$")
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

        # Fallback handler
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self._unknown_command))
