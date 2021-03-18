import datetime
import pathlib
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
LIST_DEFAULTS = "Ver plantillas de menú"
MAKE_DEFAULTS = "Crear plantilla de menú"

MENU_TYPES = {
    "DESAYUNO": "Desayuno (08:00 - 10:00)",
    "ALMUERZO": "Almuerzo (11:00 - 14:00)",
    "CAFE": "Café (15:00 - 16:00)",
    "CENA": "Cena (17:00 - 19:30)",
}

MENUS_PUBLIC = {}

DEFAULT_OPTIONS = {
    'DESAYUNO': {
        'Gallo pinto': '200',
        'Plátano maduro': '300',
        'Cereal sin leche': '300',
        'Cereal con leche': '500',
    },
    'ALMUERZO': {
        'Arroz': '200',
        'Frijoles': '100',
        'Ensalada': '200',
        'Fresco': '200',
    },
}

(
    SELECTING_MENU_DATE,
    SELECTING_MENU_TYPE,
    ADDING_MENU_ELEMENTS,
    SELECTING_MEAL_NAME,
    SELECTING_MEAL_PRICE,
    ADDING_PREDEFINED_OPTIONS

) = range(20, 26)

MENU_TYPE_CHOICE = 6
MENU_DATE_CHOICE = 7
MENU_MEALS = "meals"
MENU_TEMP_MEAL = "tmp_meal"
MENU_NEW_MEAL = "NEW_MEAL"
MENU_END_ADDING_MEAL = "END_MEALS"

CHOOSE_DATE_TO_DELETE = "date_to_delete"
CHOOSE_TYPE_TO_DELETE = "type_to_delete"

(
    CHOOSING_DATE,
    CHOOSING_TYPE,
    EDIT_MEAL,
    EDIT_PRICE,
    EDIT_MEAL_PRICE,
    CHOOSING_EDIT_MODE,
    PROCESS_EDIT_MODE
) = range(10, 17)

MEAL_EDITED = "EDITED"

CREATED_MENUS = {
    '20/03/2021': {
        'DESAYUNO': {
            'Gallo pinto': '200',
            'Omelette': '100',
            'Plátano maduro': '300',
            'Emparedados': '200',
            'Cereal sin leche': '300',
            'Cereal con leche': '500',
            'Tazón de frutas': '600'
        },
        'ALMUERZO': {
            'Arroz': '200',
            'Frijoles': '100',
            'Ensalada': '200',
            'Fresco': '200',
            'Fajitas de res': '800',
            'Risotto de hongos': '200',
            'Coliflor y brócoli': '300'
        },
        # 'CAFE': {
        #     'Rollo de jamón': '300'
        # },
        'CENA': {
            'Arroz': '200',
            'Frijoles': '100',
            'Ensalada': '200',
            'Fresco': '200',
            'Fajitas de res': '800'
        },
    }
}


class BotController:

    def __init__(self):
        self.updater = Updater(conf.BOT['TOKEN'])
        self.dispatcher = self.updater.dispatcher

        # self.dispatcher = Dispatcher(Bot(conf.BOT['TOKEN']), None, workers=0)
        # self._init_handlers()
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
            "Opción no reconocida, intente escribiendo /start para ver las opciones disponibles.",
        )

    def _start(self, update: Update, context: CallbackContext) -> None:

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
            [LIST_DEFAULTS, MAKE_DEFAULTS],
        ]

        kb = ReplyKeyboardMarkup(options, one_time_keyboard=True, resize_keyboard=True)

        update.message.reply_text(
            "Hola, seleccione una opción para continuar.",
            reply_markup=kb,
        )

    def _make_menu(self, update: Update, _: CallbackContext) -> int:

        update.message.reply_text(
            "Seleccione la fecha del nuevo menú.",
            reply_markup=telegramcalendar.create_calendar()
        )

        return SELECTING_MENU_DATE

    def _process_menu_type(self, update: Update, context: CallbackContext) -> int:
        context.user_data[MENU_TYPE_CHOICE] = update.callback_query.data

        context.user_data[MENU_MEALS] = {}

        kb = [
            [InlineKeyboardButton(text="Añadir nueva opción", callback_data=MENU_NEW_MEAL)],
        ]

        if DEFAULT_OPTIONS.get(update.callback_query.data):
            kb.append([InlineKeyboardButton(text="Añadir opciones predefinidas",
                                  callback_data=f"ADD_OPTS_DEFAULTS,{context.user_data[MENU_DATE_CHOICE]},{update.callback_query.data}")])

        update.callback_query.edit_message_text(
            text=f"El menú de <i>{MENU_TYPES.get(update.callback_query.data)}</i> "
                 f"para el día <b>{context.user_data[MENU_DATE_CHOICE]}</b> no tiene opciones.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

        return ADDING_MENU_ELEMENTS

    def _add_meal(self, update: Update, context: CallbackContext):

        if len(update.message.text) > 100:
            update.message.reply_text(
                "El nombre es demasiado largo. Intente otra vez."
            )
            return

        context.user_data[MENU_TEMP_MEAL] = update.message.text

        update.message.reply_text(
            f"Escriba el precio para <i>{update.message.text}</i>.",
            parse_mode=ParseMode.HTML
        )

        return SELECTING_MEAL_PRICE

    def _add_meal_price(self, update: Update, context: CallbackContext):

        if not all(c.isnumeric() for c in update.message.text + update.message.text.strip()):
            update.message.reply_text(
                "Solo se permiten números."
            )
            return

        if len(update.message.text) > 6:
            update.message.reply_text(
                "El precio es demasiado largo. Intente otra vez."
            )

        context.user_data[MENU_MEALS][context.user_data[MENU_TEMP_MEAL]] = update.message.text

        update.message.reply_text(
            f"El menú de <i>{MENU_TYPES.get(context.user_data.get(MENU_TYPE_CHOICE))}</i> " +
            f"para el día <b>{context.user_data[MENU_DATE_CHOICE]}</b> tiene las siguientes opciones:\n\n" +
            "{}".format("\n".join([f"₡{p}, {n}." for n, p in context.user_data[MENU_MEALS].items()])),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Añadir nueva opción", callback_data=MENU_NEW_MEAL)],
                 [InlineKeyboardButton(text="Guardar menú", callback_data=MENU_END_ADDING_MEAL)]]),
            parse_mode=ParseMode.HTML
        )

        return ADDING_MENU_ELEMENTS

    def _add_meal_price_defaults(self, update: Update, context: CallbackContext):

        if not all(c.isnumeric() for c in update.message.text + update.message.text.strip()):
            update.message.reply_text(
                "Solo se permiten números."
            )
            return

        if len(update.message.text) > 6:
            update.message.reply_text(
                "El precio es demasiado largo. Intente otra vez."
            )

        context.user_data[MENU_MEALS][context.user_data[MENU_TEMP_MEAL]] = update.message.text

        update.message.reply_text(
            f"La plantilla del menú de <i>{MENU_TYPES.get(context.user_data.get('DEFAULT_TIPO'))}</i> " +
            f"tiene las siguientes opciones:\n\n" +
            "{}".format("\n".join([f"₡{p}, {n}." for n, p in context.user_data[MENU_MEALS].items()])),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Añadir nueva opción", callback_data=MENU_NEW_MEAL)],
                 [InlineKeyboardButton(text="Guardar plantilla", callback_data=MENU_END_ADDING_MEAL)]]),
            parse_mode=ParseMode.HTML
        )

        return ADDING_MENU_ELEMENTS

    def _process_adding_meal(self, update: Update, context: CallbackContext):
        if update.callback_query.data == MENU_NEW_MEAL:

            update.callback_query.edit_message_text(
                text="Escriba el nombre de la nueva opción."
            )
            return SELECTING_MEAL_NAME

        elif update.callback_query.data == MENU_END_ADDING_MEAL:

            if not CREATED_MENUS.get(context.user_data[MENU_DATE_CHOICE]):
                CREATED_MENUS[context.user_data[MENU_DATE_CHOICE]] = {}

            CREATED_MENUS[context.user_data[MENU_DATE_CHOICE]][context.user_data[MENU_TYPE_CHOICE]] = context.user_data[
                MENU_MEALS]

            print(CREATED_MENUS)

            if MENUS_PUBLIC.get(context.user_data[MENU_DATE_CHOICE]):
                context.bot.edit_message_text(
                    text="El menú para el <b>{fecha}</b> es el siguiente:\n\n{entradas}\n\n"
                         "Nota: El texto tachado indica que esa opción del menú ya se acabó."
                        .format(
                        fecha=context.user_data[MENU_DATE_CHOICE],
                        entradas=self._make_entradas(context.user_data[MENU_DATE_CHOICE])
                    ),
                    chat_id="@comitectest",
                    message_id=MENUS_PUBLIC.get(context.user_data[MENU_DATE_CHOICE]),
                    parse_mode=ParseMode.HTML
                )

            update.callback_query.edit_message_text(
                text="Menú guardado."
            )
            return ConversationHandler.END

    def _process_adding_meal_defaults(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]
        context.user_data[MENU_MEALS] = DEFAULT_OPTIONS.get(tipo)

        update.callback_query.edit_message_text(
            f"El menú de <i>{MENU_TYPES.get(context.user_data.get(MENU_TYPE_CHOICE))}</i> " +
            f"para el día <b>{context.user_data[MENU_DATE_CHOICE]}</b> tiene las siguientes opciones:\n\n" +
            "{}".format("\n".join([f"₡{p}, {n}." for n, p in context.user_data[MENU_MEALS].items()])),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Añadir nueva opción", callback_data=MENU_NEW_MEAL)],
                 [InlineKeyboardButton(text="Guardar menú", callback_data=MENU_END_ADDING_MEAL)]]),
            parse_mode=ParseMode.HTML
        )

        return ADDING_MENU_ELEMENTS




    def _process_adding_meal_default(self, update: Update, context: CallbackContext):
        if update.callback_query.data == MENU_NEW_MEAL:

            update.callback_query.edit_message_text(
                text="Escriba el nombre de la nueva opción."
            )
            return SELECTING_MEAL_NAME

        elif update.callback_query.data == MENU_END_ADDING_MEAL:

            if not DEFAULT_OPTIONS.get(context.user_data["DEFAULT_TIPO"]):
                DEFAULT_OPTIONS[context.user_data["DEFAULT_TIPO"]] = {}

            DEFAULT_OPTIONS[context.user_data["DEFAULT_TIPO"]] = context.user_data[MENU_MEALS]

            update.callback_query.edit_message_text(
                text="Plantilla de menú guardada."
            )
            return ConversationHandler.END

    def _process_menu_date(self, update: Update, context: CallbackContext) -> int:
        selected, date_result = telegramcalendar.process_calendar_selection(context.bot, update)

        if selected:

            if date_result.date() < datetime.date.today():
                update.callback_query.answer(
                    text="No puede crear un menú para un día anterior a hoy.",
                    show_alert=True
                )

                update.callback_query.edit_message_text(
                    text="Seleccione la fecha del nuevo menú.",
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
                    text=f"Para esta fecha ya no se puede crear más menús. "
                         f"Edite uno existente o elimínelo para crear uno nuevo.",
                )
                return ConversationHandler.END

            update.callback_query.edit_message_text(
                text=f"Seleccione el tipo de menú para el día <b>{date_result.strftime('%d/%m/%Y')}</b>.",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )

            return SELECTING_MENU_TYPE

        return SELECTING_MENU_DATE

    def _list_menus(self, update: Update, _: CallbackContext):

        if len(CREATED_MENUS) == 0:
            update.message.reply_text(
                """
                No hay menús disponibles.
                """
            )
            return

        for fecha, menu in CREATED_MENUS.items():
            update.message.reply_text(
                """
                Los menús para el día <b>{fecha}</b> son los siguientes:\n\n{entradas}
                """
                    .format(
                    fecha=fecha,
                    entradas="\n\n"
                        .join([
                        "<i>{tipo}:</i>\n{meals}".format(tipo=MENU_TYPES.get(tipo),
                                                         meals="\n".join([f"₡{p}, {n}." for n, p in meals.items()]))
                        for tipo, meals in menu.items()
                        if isinstance(meals, dict)
                    ])
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Eliminar un menú", callback_data=f"DELETE_MENU,{fecha}")],
                        [InlineKeyboardButton("Editar un menú", callback_data=f"EDIT_MENU,{fecha}")],
                        [InlineKeyboardButton("Descargar menús", callback_data=f"DOWNLOAD,{fecha}")],
                        [InlineKeyboardButton("Publicar", callback_data=f"PUBLICAR,{fecha}")],
                    ]
                ),
                parse_mode=ParseMode.HTML
            )

    def _cancel(self, update: Update, _: CallbackContext):

        update.message.reply_text("Operación cancelada.")

        return ConversationHandler.END

    def _process_deleteing_menu(self, update: Update, _: CallbackContext):
        key = update.callback_query.data.split(",")[1]

        if not CREATED_MENUS.get(key):
            update.callback_query.answer(f"Nada que eliminar.")
            update.callback_query.delete_message()
            return

        kb = [[InlineKeyboardButton(MENU_TYPES.get(d), callback_data=f"MENU_TYPE_DELETE,{key},{d}")] for d in
              CREATED_MENUS.get(key).keys()]

        update.callback_query.edit_message_text(
            text="""
            Los menús para el día <b>{fecha}</b> son los siguientes:\n\n{entradas}\n\nSeleccione el menú a eliminar.
            """
                .format(
                fecha=key,
                entradas="\n\n"
                    .join([
                    "<i>{tipo}</i>:\n{meals}".format(tipo=MENU_TYPES.get(tipo),
                                                     meals="\n".join([f"₡{p}, {n}." for n, p in meals.items()]))
                    for tipo, meals in CREATED_MENUS.get(key).items()
                ])
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

    def _process_deleteing_menu_defaults(self, update: Update, _: CallbackContext):
        key = update.callback_query.data.split(",")[1]

        if not DEFAULT_OPTIONS.get(key):
            update.callback_query.answer(f"Nada que eliminar.")
            update.callback_query.delete_message()
            return

        DEFAULT_OPTIONS.pop(key)

        update.callback_query.edit_message_text(
            text="Plantilla eliminada."
        )

    def _process_deleteing_menu_type(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]

        if CREATED_MENUS.get(fecha) and CREATED_MENUS.get(fecha).get(tipo):
            CREATED_MENUS[fecha].pop(tipo)

        update.callback_query.answer("Menú eliminado.", timeout=4)

        if len(CREATED_MENUS[fecha]) == 0:
            CREATED_MENUS.pop(fecha)
            update.callback_query.delete_message()
            return

        if MENUS_PUBLIC.get(fecha):
            context.bot.edit_message_text(
                text="El menú para el <b>{fecha}</b> es el siguiente:\n\n{entradas}\n\n"
                    "Nota: El texto tachado indica que esa opción del menú ya se acabó."
                    .format(
                        fecha=fecha,
                        entradas=self._make_entradas(fecha)
                    ),
                chat_id="@comitectest",
                message_id=MENUS_PUBLIC.get(fecha),
                parse_mode=ParseMode.HTML
            )

        update.callback_query.edit_message_text(
            """
            Los menús para el día <b>{fecha}</b> son los siguientes:\n\n{entradas}
            """
                .format(
                fecha=fecha,
                entradas="\n\n"
                    .join([
                    "<i>{tipo}:</i>\n{meals}".format(tipo=MENU_TYPES.get(tipo),
                                                     meals="\n".join([f"₡{p}, {n}." for n, p in meals.items()]))
                    for tipo, meals in CREATED_MENUS.get(fecha).items()
                ])
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Eliminar un menú", callback_data=f"DELETE_MENU,{fecha}")],
                [InlineKeyboardButton("Editar un menú", callback_data=f"EDIT_MENU,{fecha}")],
                [InlineKeyboardButton("Descargar menús", callback_data=f"DOWNLOAD,{fecha}")],
                [InlineKeyboardButton("Publicar", callback_data=f"PUBLICAR,{fecha}")],
            ]),
            parse_mode=ParseMode.HTML
        )

    def _edit_menu_select(self, update: Update, _: CallbackContext):
        fecha = update.callback_query.data.split(",")[1]

        kb = [
            [InlineKeyboardButton(MENU_TYPES.get(d), callback_data=f"EDIT_SELECTION,{fecha},{d}")]
            for d in CREATED_MENUS.get(fecha).keys()
        ]

        update.callback_query.edit_message_text(
            text="""
                    Seleccione el menú a editar.
                    """,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    def _edit_menu(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]

        context.user_data["ADDED"] = {}
        context.user_data["DELETED"] = []

        kb = [
            [InlineKeyboardButton("Añadir opción", callback_data=f"ADD_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Eliminar opción", callback_data=f"DELETE_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Guardar menú", callback_data=f"EDIT_CANCEL,{fecha},{tipo}")],
        ]

        update.callback_query.edit_message_text(
            text="""
                    El menú a editar es el siguiente:\n\nFecha: <b>{fecha}</b>\n\n<i>{tipo}</i>\n{entradas}
                    """
                .format(
                fecha=fecha,
                tipo=MENU_TYPES.get(tipo),
                entradas="\n".join(
                    [
                        f"₡{price}, {meal}."
                        for meal, price in CREATED_MENUS.get(fecha).get(tipo).items()
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

    def _delete_opt(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]

        kb = [
                 [InlineKeyboardButton(f"₡{price}, {meal}.", callback_data=f"DELETE_OPT_MEAL,{fecha},{tipo},{meal}")]
                 for meal, price in CREATED_MENUS.get(fecha).get(tipo).items() if
                 meal not in context.user_data["DELETED"]
             ] + [
                 [InlineKeyboardButton(f"₡{price}, {meal}", callback_data=f"DELETE_OPT_MEAL,{fecha},{tipo},{meal}")]
                 for meal, price in context.user_data["ADDED"].items()
             ]

        update.callback_query.edit_message_text(
            text="""Seleccione la opción a eliminar.""",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    def _delete_opt_defaults(self, update: Update, context: CallbackContext):
        tipo = update.callback_query.data.split(",")[1]

        kb = [
            [InlineKeyboardButton(f"₡{price}, {meal}.", callback_data=f"DELETE_OPT_DEFAULTS,{tipo},{meal}")]
            for meal, price in DEFAULT_OPTIONS.get(tipo).items()
        ]

        update.callback_query.edit_message_text(
            text="""Seleccione la opción a eliminar.""",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    def _delete_opt_meal(self, update: Update, context: CallbackContext):
        fecha, tipo, meal = update.callback_query.data.split(",")[1:]

        if context.user_data["ADDED"].get(meal):
            context.user_data["ADDED"].pop(meal)
        else:
            context.user_data["DELETED"].append(meal)

        kb = [
            [InlineKeyboardButton("Agregar opción", callback_data=f"ADD_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Eliminar opción", callback_data=f"DELETE_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Guardar menú", callback_data=f"EDIT_CANCEL,{fecha},{tipo}")],
        ]

        update.callback_query.edit_message_text(
            text="""
                            El nuevo menú es el siguiente:\n\nFecha: <b>{fecha}</b>\n\n<i>{tipo}</i>\n{entradas}
                            """
                .format(
                fecha=fecha,
                tipo=MENU_TYPES.get(tipo),
                entradas="\n".join(
                    [
                        f"₡{price}, {m}" for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m not in context.user_data["DELETED"]
                    ] +
                    [
                        f"<i>₡{price}, {m}</i>." for m, price in context.user_data["ADDED"].items()
                    ] +
                    [
                        f"<del>₡{price}, {m}</del>." for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m in context.user_data["DELETED"]
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

    def _delete_opt_meal_defaults(self, update: Update, context: CallbackContext):
        tipo, meal = update.callback_query.data.split(",")[1:]

        if not DEFAULT_OPTIONS.get(tipo):
            update.callback_query.edit_message_text(
                "Error, la plantilla que intenta modificar ya no existe."
            )
        if DEFAULT_OPTIONS.get(tipo).get(meal):
            DEFAULT_OPTIONS.get(tipo).pop(meal)

        update.callback_query.edit_message_text(
            """
            La plantilla del menú de <b><i>{tipo}</i></b> tiene las siguientes opciones:\n\n{entradas}
            """
                .format(
                tipo=MENU_TYPES.get(tipo),
                entradas="\n".join(
                    [
                        f"₡{price}, {meal}"
                        for meal, price in DEFAULT_OPTIONS.get(tipo).items()
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Eliminar esta plantilla", callback_data=f"DELETE_MENU_DEFAULTS,{tipo}")],
                    [InlineKeyboardButton("Eliminar una opción", callback_data=f"DELETE_MENU_DEFAULTS_OPT,{tipo}")],
                    [InlineKeyboardButton("Agregar una opción", callback_data=f"ADD_OPT_DEFAULTS,{tipo}")]
                ]
            ),
            parse_mode=ParseMode.HTML
        )

    def _edit_cancel(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]

        if not CREATED_MENUS.get(fecha) or not CREATED_MENUS.get(fecha).get(tipo):
            update.callback_query.edit_message_text(
                "Error, el menú que intenta modificar ya no existe."
            )
            return

        for e in context.user_data["DELETED"]:
            CREATED_MENUS.get(fecha).get(tipo).pop(e)

        CREATED_MENUS.get(fecha).get(tipo).update(context.user_data["ADDED"])

        if len(context.user_data["DELETED"]) > 0 or len(context.user_data["ADDED"]) > 0 and MENUS_PUBLIC.get(context.user_data[MENU_DATE_CHOICE]):
            context.bot.edit_message_text(
                text="El menú para el <b>{fecha}</b> es el siguiente:\n\n{entradas}\n\n"
                    "Nota: El texto tachado indica que esa opción del menú ya se acabó."
                    .format(
                        fecha=fecha,
                        entradas=self._make_entradas(fecha)
                    ),
                chat_id="@comitectest",
                message_id=MENUS_PUBLIC.get(context.user_data[MENU_DATE_CHOICE]),
                parse_mode=ParseMode.HTML
            )

        update.callback_query.edit_message_text(
            """
            Los menús para el día <b>{fecha}</b> son los siguientes:\n\n{entradas}
            """
                .format(
                fecha=fecha,
                entradas="\n\n"
                    .join([
                    "<i>{tipo}:</i>\n{meals}".format(tipo=MENU_TYPES.get(tipo),
                                                     meals="\n".join([f"₡{p}, {n}." for n, p in meals.items()]))
                    for tipo, meals in CREATED_MENUS.get(fecha).items()
                ])
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Eliminar un menú", callback_data=f"DELETE_MENU,{fecha}")],
                    [InlineKeyboardButton("Editar un menú", callback_data=f"EDIT_MENU,{fecha}")],
                    [InlineKeyboardButton("Descargar menús", callback_data=f"DOWNLOAD,{fecha}")],
                    [InlineKeyboardButton("Publicar", callback_data=f"PUBLICAR,{fecha}")],
                ]),
            parse_mode=ParseMode.HTML
        )

    def _add_opt(self, update: Update, context: CallbackContext):
        fecha, tipo = update.callback_query.data.split(",")[1:]

        context.user_data["ADD_OPT_FECHA"] = fecha
        context.user_data["ADD_OPT_TIPO"] = tipo

        update.callback_query.delete_message()

        update.effective_chat.send_message(text="""Escriba el nombre de la nueva opción.""")

        return 40

    def _add_opt_defaults(self, update: Update, context: CallbackContext):
        tipo = update.callback_query.data.split(",")[1]

        context.user_data["ADD_OPT_TIPO"] = tipo

        update.callback_query.delete_message()

        update.effective_chat.send_message(text="""Escriba el nombre de la nueva opción.""")

        return 40

    def _add_opt_meal(self, update: Update, context: CallbackContext):

        if len(update.message.text) > 100:
            update.message.reply_text(
                "El nombre es demasiado largo. Intente otra vez."
            )

        context.user_data["OPT_TEMP"] = update.message.text

        update.message.reply_text(
            text=f"Escriba el precio de <i>{update.message.text}</i>.",
            parse_mode=ParseMode.HTML
        )

        return 50

    def _add_opt_price(self, update: Update, context: CallbackContext):

        if len(update.message.text) > 6:
            update.message.reply_text(
                "El precio es demasiado largo. Intente otra vez."
            )

        fecha = context.user_data["ADD_OPT_FECHA"]
        tipo = context.user_data["ADD_OPT_TIPO"]

        if not all(c.isnumeric() for c in update.message.text + update.message.text.strip()):
            update.message.reply_text(
                "Por favor ingrese solo números."
            )
            return

        context.user_data["ADDED"][context.user_data["OPT_TEMP"]] = update.message.text

        kb = [
            [InlineKeyboardButton("Agregar opción", callback_data=f"ADD_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Eliminar opción", callback_data=f"DELETE_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Guardar menú", callback_data=f"EDIT_CANCEL,{fecha},{tipo}")],
        ]

        update.message.reply_text(
            text="""
                El nuevo menú es el siguiente:\n\nFecha: <b>{fecha}</b>\n<i>{tipo}</i>\n{entradas}
                """
                .format(
                fecha=fecha,
                tipo=tipo,
                entradas="\n".join(
                    [
                        f"₡{price}, {m}." for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m not in context.user_data["DELETED"]
                    ] +
                    [
                        f"<i>₡{price}, {m}</i>." for m, price in context.user_data["ADDED"].items()
                    ] +
                    [
                        f"<del>₡{price}, {m}</del>." for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m in context.user_data["DELETED"]
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

        return ConversationHandler.END

    def _add_opt_price_defaults(self, update: Update, context: CallbackContext):

        if len(update.message.text) > 6:
            update.message.reply_text(
                "El precio es demasiado largo. Intente otra vez."
            )
            return

        if not all(c.isnumeric() for c in update.message.text + update.message.text.strip()):
            update.message.reply_text(
                "Por favor ingrese solo números."
            )
            return

        tipo = context.user_data["ADD_OPT_TIPO"]

        if not DEFAULT_OPTIONS.get(tipo):
            update.message.reply_text("Error, la plantilla que intenta modificar ya no existe.")
            return ConversationHandler.END

        DEFAULT_OPTIONS.get(tipo)[context.user_data["OPT_TEMP"]] = update.message.text

        update.message.reply_text(
            """
            La plantilla del menú de <b><i>{tipo}</i></b> tiene las siguientes opciones:\n\n{entradas}
            """
                .format(
                tipo=MENU_TYPES.get(tipo),
                entradas="\n".join(
                    [
                        f"₡{price}, {meal}"
                        for meal, price in DEFAULT_OPTIONS.get(tipo).items()
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Eliminar esta plantilla", callback_data=f"DELETE_MENU_DEFAULTS,{tipo}")],
                    [InlineKeyboardButton("Eliminar una opción", callback_data=f"DELETE_MENU_DEFAULTS_OPT,{tipo}")],
                    [InlineKeyboardButton("Agregar una opción", callback_data=f"ADD_OPT_DEFAULTS,{tipo}")]
                ]
            ),
            parse_mode=ParseMode.HTML
        )

        return ConversationHandler.END

    def _cancel_add_opt(self, update: Update, context: CallbackContext):

        update.message.reply_text("Operación cancelada.")

        fecha = context.user_data["ADD_OPT_FECHA"]
        tipo = context.user_data["ADD_OPT_TIPO"]

        kb = [
            [InlineKeyboardButton("Agregar opción", callback_data=f"ADD_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Eliminar opción", callback_data=f"DELETE_OPT,{fecha},{tipo}")],
            [InlineKeyboardButton("Guardar menú", callback_data=f"EDIT_CANCEL,{fecha},{tipo}")],
        ]

        update.message.reply_text(
            text="""
                        El nuevo menú es el siguiente:\n\nFecha: {fecha}\n{tipo}\n{entradas}
                        """
                .format(
                fecha=fecha,
                tipo=tipo,
                entradas="\n".join(
                    [
                        f"₡{price}, {m}" for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m not in context.user_data["DELETED"]
                    ] +
                    [
                        f"<i>₡{price}, {m}</i>." for m, price in context.user_data["ADDED"].items()
                    ] +
                    [
                        f"<del>₡{price}, {m}</del>." for m, price in CREATED_MENUS.get(fecha).get(tipo).items()
                        if m in context.user_data["DELETED"]
                    ]
                )
            ),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )

        return ConversationHandler.END

    def _make_menu_defaults(self, update: Update, _: CallbackContext) -> int:

        kb = [
            [InlineKeyboardButton(MENU_TYPES.get(d), callback_data=f"MAKE_MENU_DEFAULTS,{d}")]
            for d in MENU_TYPES.keys() if d not in DEFAULT_OPTIONS.keys()
        ]

        update.message.reply_text(
            "Seleccione el tipo de menú.",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        return SELECTING_MENU_TYPE

    def _process_menu_type_defaults(self, update: Update, context: CallbackContext) -> int:

        tipo = update.callback_query.data.split(",")[1]

        context.user_data["DEFAULT_TIPO"] = tipo

        context.user_data[MENU_MEALS] = {}

        update.callback_query.edit_message_text(
            text=f"La plantilla del menú de <i>{MENU_TYPES.get(tipo)}</i> "
                 f"no tiene opciones.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Añadir nueva opción", callback_data=MENU_NEW_MEAL)]]),
            parse_mode=ParseMode.HTML
        )

        return ADDING_MENU_ELEMENTS

    def _list_menus_defaults(self, update: Update, _: CallbackContext):

        if len(DEFAULT_OPTIONS) == 0:
            update.message.reply_text(
                """
                No hay plantillas disponibles.
                """
            )
            return

        for tipo, menu in DEFAULT_OPTIONS.items():
            update.message.reply_text(
                """
                La plantilla del menú de <b><i>{tipo}</i></b> tiene las siguientes opciones:\n\n{entradas}
                """
                    .format(
                    tipo=MENU_TYPES.get(tipo),
                    entradas="\n".join(
                        [
                            f"₡{price}, {meal}"
                            for meal, price in menu.items()
                        ]
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Eliminar esta plantilla", callback_data=f"DELETE_MENU_DEFAULTS,{tipo}")],
                        [InlineKeyboardButton("Eliminar una opción", callback_data=f"DELETE_MENU_DEFAULTS_OPT,{tipo}")],
                        [InlineKeyboardButton("Agregar una opción", callback_data=f"ADD_OPT_DEFAULTS,{tipo}")]
                    ]
                ),
                parse_mode=ParseMode.HTML
            )

    def _download(self, update: Update, context: CallbackContext):
        fecha = update.callback_query.data.split(",")[1]

        update.effective_chat.send_document(
            open("slides.pdf", "rb"),
            f"Menu_{fecha.replace('/', '-')}"
        )

    def _publicar(self, update: Update, context: CallbackContext):
        fecha = update.callback_query.data.split(",")[1]

        MENUS_PUBLIC[fecha] = context.bot.send_message(
            chat_id="@comitectest",
            parse_mode=ParseMode.HTML,
            text=
            "El menú para el <b>{fecha}</b> es el siguiente:\n\n{entradas}\n\n"
            "Nota: El texto tachado indica que esa opción del menú ya se acabó."
            .format(
                fecha=fecha,
                entradas=self._make_entradas(fecha)
            )
        ).message_id

    def _make_entradas(self, fecha: str):
        return "\n\n".join([
            "<i>{tipo}</i>\n{meals}".format(
                tipo=MENU_TYPES.get(elm),
                meals="\n".join(
                    [
                        f"₡{price}, {meal}"
                        for meal, price in CREATED_MENUS.get(fecha).get(elm).items()
                    ] if CREATED_MENUS.get(fecha).get(elm) else
                    ["Por definir."]
                )
            ) for elm in MENU_TYPES.keys()
        ])



    class SecurityFilter(UpdateFilter):
        def filter(self, update: Update):
            user = update.message.bot.get_chat_member(conf.BOT["ADMIN_GROUP"],
                                                      update.message.from_user.id)

            return user is not None and user.status in ["administrator", "creator"]

    def _init_handlers(self):

        # self.dispatcher.add_handler(MessageHandler(~self.SecurityFilter(), lambda update, _: update.message.reply_text("FUCK YOU")))

        self.dispatcher.add_handler(CommandHandler("start", self._menus))

        self.dispatcher.add_handler(MessageHandler(Filters.regex(f"^{LIST_MENUS}$"), self._list_menus))

        self.dispatcher.add_handler(MessageHandler(Filters.regex(f"^{LIST_DEFAULTS}$"), self._list_menus_defaults))

        self.dispatcher.add_handler(CallbackQueryHandler(self._process_deleteing_menu, pattern=f"^(DELETE_MENU,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._publicar, pattern=f"^(PUBLICAR,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._download, pattern=f"^(DOWNLOAD,.*)$"))

        self.dispatcher.add_handler(
            CallbackQueryHandler(self._process_deleteing_menu_defaults, pattern=f"^(DELETE_MENU_DEFAULTS,.*)$"))

        self.dispatcher.add_handler(
            CallbackQueryHandler(self._process_deleteing_menu_type, pattern=f"^(MENU_TYPE_DELETE.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._edit_menu_select, pattern=f"^(EDIT_MENU,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._edit_menu, pattern=f"^(EDIT_SELECTION,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._edit_cancel, pattern=f"^(EDIT_CANCEL,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._delete_opt, pattern=f"^(DELETE_OPT,.*)$"))

        self.dispatcher.add_handler(
            CallbackQueryHandler(self._delete_opt_defaults, pattern=f"^(DELETE_MENU_DEFAULTS_OPT,.*)$"))

        self.dispatcher.add_handler(
            CallbackQueryHandler(self._delete_opt_meal_defaults, pattern=f"^(DELETE_OPT_DEFAULTS,.*)$"))

        self.dispatcher.add_handler(CallbackQueryHandler(self._delete_opt_meal, pattern=f"^(DELETE_OPT_MEAL,.*)$"))

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(self._add_opt, pattern=f"^(ADD_OPT,.*)$")],
            states={
                40: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_opt_meal),
                ],
                50: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_opt_price),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_add_opt),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[CallbackQueryHandler(self._add_opt_defaults, pattern=f"^(ADD_OPT_DEFAULTS,.*)$")],
            states={
                40: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_opt_meal),
                ],
                50: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_opt_price_defaults),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel_add_opt),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

        self.dispatcher.add_handler(ConversationHandler(
            entry_points=[MessageHandler(Filters.regex(f"^{MAKE_DEFAULTS}$"), self._make_menu_defaults)],
            states={
                SELECTING_MENU_TYPE: [
                    CallbackQueryHandler(self._process_menu_type_defaults,
                                         pattern=f"^"
                                                 f"(MAKE_MENU_DEFAULTS,.*)"
                                                 f"$")
                ],
                ADDING_MENU_ELEMENTS: [
                    CallbackQueryHandler(self._process_adding_meal_default,
                                         pattern=f"^({MENU_NEW_MEAL})|({MENU_END_ADDING_MEAL})$")
                ],
                SELECTING_MEAL_NAME: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_meal),
                ],
                SELECTING_MEAL_PRICE: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_meal_price_defaults),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

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
                    CallbackQueryHandler(self._process_adding_meal_defaults,
                                         pattern=f"^(ADD_OPTS_DEFAULTS.*)$"),
                    CallbackQueryHandler(self._process_adding_meal,
                                         pattern=f"^({MENU_NEW_MEAL})|({MENU_END_ADDING_MEAL})$")
                ],
                SELECTING_MEAL_NAME: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_meal),
                ],
                SELECTING_MEAL_PRICE: [
                    MessageHandler(Filters.text & ~Filters.command, self._add_meal_price),
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                MessageHandler(Filters.text & ~Filters.command, self._unknown_command)
            ],
        ))

        # Fallback handler
        self.dispatcher.add_handler(MessageHandler(Filters.text, self._unknown_command))
