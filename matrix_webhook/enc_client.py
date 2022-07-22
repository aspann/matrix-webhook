"""EncryptedClient for Matrix Webhook."""

import asyncio
import logging
import json
import os
import sys

from nio import (
    AsyncClient,
    ClientConfig,
    InviteEvent,
    KeyVerificationCancel,
    KeyVerificationEvent,
    KeyVerificationKey,
    KeyVerificationMac,
    KeyVerificationStart,
    LoginResponse,
    MatrixRoom,
    RoomMemberEvent,
)
from nio.store.database import DefaultStore
from typing import Optional
from . import conf

SESSION_DETAILS_FILE = "creds.json"
LOGGER = logging.getLogger("matrix_webhook.enc_client")

class AsyncEncClient(AsyncClient):
    verified_devices=[]
    def __init__(
        self,
        homeserver,
        user="",
        device_id="",
        store_path="store",
        config = ClientConfig(
            store_sync_tokens=True, 
            encryption_enabled=True,
            store = DefaultStore
        ),
        ssl=None,
        proxy=None,
    ):
        super().__init__(
            homeserver,
            user=user,
            device_id=device_id,
            store_path=store_path,
            config=config,
            ssl=ssl,
            proxy=proxy,
        )

        # if the store location doesn't exist, we'll make it
        if store_path and not os.path.isdir(store_path):
            os.mkdir(store_path)

        self.add_event_callback(self.autojoin_room, InviteEvent)
        self.add_event_callback(self.room_member_changed, RoomMemberEvent)
        self.add_event_callback(self.key_verification, KeyVerificationEvent)


    async def login(self) -> None:
        if os.path.exists(SESSION_DETAILS_FILE) and os.path.isfile(
            SESSION_DETAILS_FILE
        ):
            try:
                with open(SESSION_DETAILS_FILE, "r") as f:
                    config = json.load(f)
                    self.access_token = config["access_token"]
                    self.user_id = config["user_id"]
                    self.device_id = config["device_id"]

                    self.load_store()
                    LOGGER.info(f"Logged in using stored credentials: {self.user_id} on {self.device_id}")

            except IOError as err:
                LOGGER.error(f"Couldn't load session from file. Logging in. Error: {err}")
            except json.JSONDecodeError:
                LOGGER.error("Couldn't read JSON file; overwriting")

        if not self.user_id or not self.access_token or not self.device_id:
            resp = await super().login(conf.MATRIX_PW)

            if isinstance(resp, LoginResponse):
                LOGGER.info("Logged in using a password; saving details to disk")
                self.__write_details_to_disk(resp)
            else:
                LOGGER.warning(f"Failed to log in: {resp}")
                sys.exit(1)

    def trust_devices(self, user_id: str, device_list: Optional[str] = None) -> None:
        for device_id, olm_device in self.device_store[user_id].items():
            if (device_list and device_id not in device_list) or \
                (user_id == self.user_id and device_id == self.device_id) or \
                (user_id + device_id in self.verified_devices):
                LOGGER.debug(f"Device {device_id} from user {user_id} already trusted")
                continue

            self.verify_device(olm_device)
            self.verified_devices.append(user_id + device_id)
            LOGGER.debug(f"Trusting {device_id} from user {user_id}")

    async def autojoin_room(self, room: MatrixRoom, event: InviteEvent):
        await self.join(room.room_id)
        LOGGER.debug(f"Room {room.name} is encrypted: {room.encrypted}")
        ## if invited after sync was already done
        for user in room.users:
            self.trust_devices(user)

    async def room_member_changed(self, room: MatrixRoom, event: RoomMemberEvent):
        LOGGER.info(f"RoomMemberEvent: {event.state_key}: {event.membership}")
        if event.membership == "join":
            self.trust_devices(event.state_key)

    async def join_room(self, room_id: str):
        await self.join(room_id)
        room = self.rooms[room_id]
        LOGGER.debug(f"Room {room.name} is encrypted: {room.encrypted}")

    # TODO: WIP (not working as expected)
    async def key_verification(self, room: MatrixRoom, event: KeyVerificationEvent):
        LOGGER.info(f"KeyVerificationEvent: {event}")
        try:
            if isinstance(event, KeyVerificationStart): # 1.
                LOGGER.debug("KeyVerificationStart")
                return
            elif isinstance(event, KeyVerificationKey): # 2.
                LOGGER.debug("KeyVerificationKey")
                return
            elif isinstance(event, KeyVerificationMac): # 3.
                LOGGER.debug("KeyVerificationMac")
                return
            elif isinstance(event, KeyVerificationCancel): # anytime
                LOGGER.debug("KeyVerificationCancel")
                return
            else: # cancel/unknown
                LOGGER.debug("Unknown KeyVerification")
                return
        except:
            LOGGER.error("An error occured during key verification!")


    @staticmethod
    def __write_details_to_disk(resp: LoginResponse) -> None:
        with open(SESSION_DETAILS_FILE, "w") as f:
            json.dump({
                "access_token": resp.access_token,
                "device_id": resp.device_id,
                "user_id": resp.user_id,
            }, f)

async def run(self) -> None:
    await self.login()

    async def after_first_sync():
        await self.synced.wait()
        # check if it's needed to upload our keys
        if self.should_upload_keys:
            await self.keys_upload()
        # trusting all users in all rooms (incl. all devices)
        for room in self.rooms:
            if not self.rooms[room].users:
                LOGGER.error(f"No users in room: {room.name}")
            else:
                for user in self.rooms[room].users:
                    self.trust_devices(user)

    after_first_sync_task = asyncio.ensure_future(after_first_sync())
    sync_forever_task = asyncio.ensure_future(
        self.sync_forever(30000, full_state=True)
    )

    await asyncio.gather(
        after_first_sync_task,
        sync_forever_task,
    )
