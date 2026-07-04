from aiogram.fsm.state import State, StatesGroup


class AddBook(StatesGroup):
    title = State()
    author = State()
    file = State()
    reward = State()
    category = State()


class AddTariff(StatesGroup):
    name = State()
    price = State()
    duration = State()
    category = State()
    description = State()


class AddTask(StatesGroup):
    title = State()
    description = State()


class Deposit(StatesGroup):
    choosing_tariff = State()
    waiting_receipt = State()


class Withdraw(StatesGroup):
    amount = State()
    card = State()
