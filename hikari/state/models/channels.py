#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © Nekoka.tt 2019
#
# This file is part of Hikari.
#
# Hikari is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hikari is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Hikari. If not, see <https://www.gnu.org/licenses/>.
"""
Channel models.
"""
from __future__ import annotations

import abc
import typing

from hikari.state import state_registry
from hikari.state.models import interfaces
from hikari.state.models import guilds as _guild
from hikari.state.models import overwrites
from hikari.state.models import users
from hikari.internal_utilities import auto_repr
from hikari.internal_utilities import data_structures
from hikari.internal_utilities import transformations


class Channel(abc.ABC, interfaces.ISnowflake, interfaces.IStateful):
    """
    A generic type of channel.

    Note:
        As part of the contract for this class being volatile, once initialized, the `update_state` method will be
        invoked, thus one should set any dependent fields in the constructor BEFORE invoking super where possible
        or the fields will not be initialized when accessed.
    """

    __slots__ = ("_state", "id")

    #: Channel implementations provided.
    _channel_implementations: typing.ClassVar[typing.Dict[int, typing.Type[Channel]]] = {}

    #: True if the class is a DM channel class, False otherwise.
    #:
    #: :type: :class:`bool`
    is_dm: typing.ClassVar[bool]

    #: The integer type of the class.
    #:
    #: :type: :class:`int`
    type: typing.ClassVar[int]

    _state: state_registry.IStateRegistry

    #: The ID of the channel.
    #:
    #: :type: :class:`int`
    id: int

    @abc.abstractmethod
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT):
        self._state = global_state
        self.id = int(payload["id"])
        self.update_state(payload)

    @abc.abstractmethod
    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        ...

    def __init_subclass__(cls, **kwargs):
        if "type" in kwargs:
            cls.type = kwargs.pop("type")
            cls._channel_implementations[cls.type] = cls
        cls.is_dm = kwargs.pop("is_dm", NotImplemented)


class TextChannel(Channel):
    """
    Any class that can have messages sent to it.

    This class itself will not behave as a dataclass, and is a trait for Channels that have the ability to
    send and receive messages to implement as a basic interface.
    """

    __slots__ = ()

    #: The optional ID of the last message to be sent.
    #:
    #: :type: :class:`int` or `None`
    last_message_id: typing.Optional[int]

    @abc.abstractmethod
    def __init__(self, global_state, payload):
        super().__init__(global_state, payload)


class GuildChannel(Channel, is_dm=False):
    """
    A channel that belongs to a guild.
    """

    __slots__ = ("guild_id", "position", "permission_overwrites", "name", "parent_id")

    #: The guild's ID.
    #:
    #: :type: :class:`int`
    guild_id: int

    #: The parent channel ID.
    #:
    #: :type: :class:`int` or :class:`None`
    parent_id: typing.Optional[int]

    #: The position of the channel in the channel list.
    #:
    #: :type: :class:`int`
    position: int

    #: A sequence t of permission overwrites for this channel.
    #:
    #: :type: :class:`typing.Sequence` of :attr:`hikari.core.models.overwrites.Overwrite`
    permission_overwrites: typing.Sequence[overwrites.Overwrite]

    #: The name of the channel.
    #:
    #: :type: :class:`str`
    name: str

    @abc.abstractmethod
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT):
        self.guild_id = int(payload["guild_id"])
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        self.position = int(payload["position"])

        overwrite_objs = []

        for raw_overwrite in payload["permission_overwrites"]:
            overwrite_obj = overwrites.Overwrite(raw_overwrite)
            overwrite_objs.append(overwrite_obj)

        self.permission_overwrites = overwrite_objs
        self.name = payload["name"]
        self.parent_id = transformations.nullable_cast(payload.get("parent_id"), int)

    @property
    def guild(self) -> _guild.Guild:
        return self._state.get_guild_by_id(self.guild_id)

    @property
    def parent(self) -> typing.Optional[GuildCategory]:
        return self.guild.channels[self.parent_id] if self.parent_id is not None else None


class GuildTextChannel(GuildChannel, TextChannel, type=0, is_dm=False):
    """
    A text channel.
    """

    __slots__ = ("topic", "rate_limit_per_user", "last_message_id", "nsfw")

    #: The channel topic.
    #:
    #: :type: :class:`str` or `None`
    topic: typing.Optional[str]

    #: How many seconds a user has to wait before sending consecutive messages.
    #:
    #: :type: :class:`int`
    rate_limit_per_user: int

    #: The optional ID of the last message to be sent.
    #:
    #: :type: :class:`int` or `None`
    last_message_id: typing.Optional[int]

    #: Whether the channel is NSFW or not
    #:
    #: :type: :class:`bool`
    nsfw: bool

    __repr__ = auto_repr.repr_of("id", "name", "guild.name", "nsfw")

    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT):
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        super().update_state(payload)
        self.nsfw = payload.get("nsfw", False)
        self.topic = payload.get("topic")
        self.rate_limit_per_user = payload.get("rate_limit_per_user", 0)
        self.last_message_id = transformations.nullable_cast(payload.get("last_message_id"), int)


class DMChannel(TextChannel, type=1, is_dm=True):
    """
    A DM channel between users.
    """

    __slots__ = ("last_message_id", "recipients")

    #: The optional ID of the last message to be sent.
    #:
    #: :type: :class:`int` or `None`
    last_message_id: typing.Optional[int]

    #: Sequence of recipients in the DM chat.
    #:
    #: :type: :class:`typing.Sequence` of :class:`hikari.core.models.users.User`
    recipients: typing.Sequence[users.User]

    __repr__ = auto_repr.repr_of("id")

    # noinspection PyMissingConstructor
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT):
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        super().update_state(payload)
        self.last_message_id = transformations.nullable_cast(payload.get("last_message_id"), int)
        self.recipients = [self._state.parse_user(u) for u in payload.get("recipients", data_structures.EMPTY_SEQUENCE)]


class GuildVoiceChannel(GuildChannel, type=2, is_dm=False):
    """
    A voice channel within a guild.
    """

    __slots__ = ("bitrate", "user_limit")

    #: Bit-rate of the voice channel.
    #:
    #: :type: :class:`int`
    bitrate: int

    #: The max number of users in the voice channel, or None if there is no limit.
    #:
    #: :type: :class:`int` or `None`
    user_limit: typing.Optional[int]

    __repr__ = auto_repr.repr_of("id", "name", "guild.name", "bitrate", "user_limit")

    # noinspection PyMissingConstructor
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT):
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        super().update_state(payload)
        self.bitrate = payload.get("bitrate") or None
        self.user_limit = payload.get("user_limit") or None


class GroupDMChannel(DMChannel, type=3, is_dm=True):
    """
    A DM group chat.
    """

    __slots__ = ("icon_hash", "name", "owner_id", "owner_application_id")

    #: The ID of the person or application that owns this channel currently.
    #:
    #: :type: :class:`int`
    owner_id: int

    #: Hash of the icon for the chat, if there is one.
    #:
    #: :type: :class:`str` or `None`
    icon_hash: typing.Optional[str]

    #: Name for the chat, if there is one.
    #:
    #: :type: :class:`str` or `None`
    name: typing.Optional[str]

    #: If the chat was made by a bot, this will be the application ID of the bot that made it. For all other cases it
    #: will be `None`.
    #:
    #: :type: :class:`int` or `None`
    owner_application_id: typing.Optional[int]

    __repr__ = auto_repr.repr_of("id", "name")

    # noinspection PyMissingConstructor
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT) -> None:
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        super().update_state(payload)
        self.icon_hash = payload.get("icon")
        self.name = payload.get("name")
        self.owner_application_id = transformations.nullable_cast(payload.get("application_id"), int)
        self.owner_id = transformations.nullable_cast(payload.get("owner_id"), int)


class GuildCategory(GuildChannel, type=4, is_dm=False):
    """
    A category within a guild.
    """

    __slots__ = ()

    __repr__ = auto_repr.repr_of("id", "name", "guild.name")

    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT) -> None:
        super().__init__(global_state, payload)


class GuildNewsChannel(GuildChannel, type=5, is_dm=False):
    """
    A channel for news topics within a guild.
    """

    __slots__ = ("topic", "last_message_id", "nsfw")

    #: The channel topic.
    #:
    #: :type: :class:`str` or `None`
    topic: typing.Optional[str]

    #: The optional ID of the last message to be sent.
    #:
    #: :type: :class:`int` or `None`
    last_message_id: typing.Optional[int]

    #: Whether the channel is NSFW or not
    #:
    #: :type: :class:`bool`
    nsfw: bool

    __repr__ = auto_repr.repr_of("id", "name", "guild.name", "nsfw")

    # noinspection PyMissingConstructor
    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT) -> None:
        super().__init__(global_state, payload)

    def update_state(self, payload: data_structures.DiscordObjectT) -> None:
        super().update_state(payload)
        self.nsfw = payload.get("nsfw", False)
        self.topic = payload.get("topic")
        self.last_message_id = transformations.nullable_cast(payload.get("last_message_id"), int)


class GuildStoreChannel(GuildChannel, type=6, is_dm=False):
    """
    A store channel for selling of games within a guild.
    """

    __slots__ = ()

    __repr__ = auto_repr.repr_of("id", "name", "guild.name")

    def __init__(self, global_state: state_registry.IStateRegistry, payload: data_structures.DiscordObjectT) -> None:
        super().__init__(global_state, payload)


# noinspection PyProtectedMember
def is_channel_type_dm(channel_type: int) -> bool:
    """
    Returns True if a raw channel type is for a DM. If a channel type is given that is not recognised, then it returns
    `False` regardless.

    This is only used internally, there is no other reason for you to use this outside of framework-internal code.
    """
    return getattr(Channel._channel_implementations.get(channel_type), "is_dm", False)


# noinspection PyProtectedMember
def parse_channel(
    global_state, payload
) -> typing.Union[
    GuildTextChannel, DMChannel, GuildVoiceChannel, GroupDMChannel, GuildCategory, GuildNewsChannel, GuildStoreChannel
]:
    """
    Parse a channel from a channel payload from an API call.

    Args:
        global_state:
            the global state object.
        payload:
            the payload to parse.

    Returns:
        A subclass of :class:`Channel` as appropriate for the given payload provided.
    """
    channel_type = payload.get("type")

    if channel_type in Channel._channel_implementations:
        channel_type = Channel._channel_implementations[channel_type]
        channel = channel_type(global_state, payload)
        return channel
    else:
        raise TypeError(f"Invalid channel type {channel_type}") from None


__all__ = (
    "Channel",
    "GuildChannel",
    "GuildTextChannel",
    "DMChannel",
    "GuildVoiceChannel",
    "GroupDMChannel",
    "GuildCategory",
    "GuildNewsChannel",
    "GuildStoreChannel",
)