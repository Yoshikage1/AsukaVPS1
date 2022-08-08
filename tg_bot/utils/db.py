# below code is taken from USERGE-X repo
# all credits to the respective author (dunno who wrote it will find later n update)


__all__ = ['get_collection']

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticClient, AgnosticDatabase, AgnosticCollection
DB_URL = "mongodb+srv://xelcius:raizel~97@cluster0.gj9j8.mongodb.net/cluster0?retryWrites=true&w=majority"

print("Connecting to Database ...")

_MGCLIENT: AgnosticClient = AsyncIOMotorClient(DB_URL)
_RUN = asyncio.get_event_loop().run_until_complete

if "Asuka" in _RUN(_MGCLIENT.list_database_names()):
    print("Asuka Database Found :) => Now Logging to it...")
else:
    print("Asuka Database Not Found :( => Creating New Database...")

_DATABASE: AgnosticDatabase = _MGCLIENT["Asuka"]


def get_collection(name: str) -> AgnosticCollection:
    """ Create or Get Collection from your database """
    return _DATABASE[name]


def _close_db() -> None:
    _MGCLIENT.close()
