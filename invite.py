import os
import json
import random
import asyncio
import logging
import requests

from pyrogram import Client, filters, types, enums

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN", "7622381294:AAFE-gak873KscvFdmkIP-vadwiUefzytrw")
API_ID = int(os.environ.get("API_ID", 17181316)) 
API_HASH = os.environ.get("API_HASH", "23d91521902fbde6dd061d0b959de764git") 

DATA_FILE = "group_data.json"
group_data = {}
MAX_GROUPS = 9 

def load_group_data():
    global group_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                loaded_data = json.load(f)
                for chat_id_str, data in loaded_data.items():
                    chat_id = int(chat_id_str)
                    if "user_data" in data:
                        temp_user_data = {}
                        for user_id_str, user_info in data["user_data"].items():
                            user_id = int(user_id_str)
                            if "invited_user_ids" in user_info and isinstance(user_info["invited_user_ids"], list):
                                user_info["invited_user_ids"] = set(user_info["invited_user_ids"])
                            temp_user_data[user_id] = user_info
                        data["user_data"] = temp_user_data
                    group_data[chat_id] = data
                logger.info(f"Данные загружены из {DATA_FILE}. Всего активных групп: {len(group_data)}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных из {DATA_FILE}: {e}")
            group_data = {}
    else:
        logger.info(f"Файл данных {DATA_FILE} не найден. Инициализация пустых данных.")

def save_group_data():
    data_to_save = {}
    for chat_id, data in group_data.items():
        temp_data = data.copy()
        if "user_data" in temp_data:
            temp_user_data = {}
            for user_id, user_info in temp_data["user_data"].items():
                temp_user_info = user_info.copy()
                if "invited_user_ids" in temp_user_info and isinstance(temp_user_info["invited_user_ids"], set):
                    temp_user_info["invited_user_ids"] = list(temp_user_info["invited_user_ids"])
                temp_user_data[str(user_id)] = temp_user_info
            temp_data["user_data"] = temp_user_data
        data_to_save[str(chat_id)] = temp_data

    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        logger.info(f"Данные сохранены в {DATA_FILE}.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в {DATA_FILE}: {e}")

def get_group_data(chat_id):
    if chat_id not in group_data:
        if len(group_data) >= MAX_GROUPS:
            logger.warning(f"Превышено максимальное количество групп ({MAX_GROUPS}). Невозможно инициализировать данные для чата: {chat_id}")
            return None
        group_data[chat_id] = {
            "collection_active": False,
            "user_data": {},
            "participants": [],
            "last_pinned_message_id": None
        }
        logger.info(f"Инициализированы данные для нового чата: {chat_id}. Всего активных групп: {len(group_data)}")
        save_group_data()
    return group_data[chat_id]

def full_name(user: types.User) -> str:
    return f"{user.first_name}{' ' + user.last_name if user.last_name else ''}"

async def get_emojis() -> list[str]:
    emojis_list = ['😀', '😃', '😄', '😁', '😆', '😅', '😂', '🤣', '😊', '😇', '🙂', '🙃', '😉', '😌', '😍', '🥰', '😘', '😗', '😙', '😚', '😋', '😛', '😝', '😜', '🤪', '🤨', '🧐', '🤓', '😎', '🤩', '🥳', '😏', '😒', '😞', '😔', '😟', '😕', '🙁', '☹️', '😣', '😖', '😫', '😩', '🥺', '😤', '😠', '😡', '🤬', '🤯', '😳', '🥵', '🥶', '😱', '😨', '😰', '😢', '😭', '😥', '😓', '🫠', '🤭', '🤫', '🤥', '😶', '😐', '😑', '🫨', '😬', '🫠', '🙄', '🫡', '🤔', '🫣', '🫡', '🤫', '🤤', '😴', '😷', '🤒', '🤕', '🤮', '🤢', '🤧', '😇', '🥳', '🥸', '🫠', '😶', '🤫', '🤔', '🤨', '🧐', '🤓', '🫡', '🫣', '🫠']
    return emojis_list


app = Client(
    'zazyvala_bot',
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN,
    parse_mode=enums.ParseMode.HTML
)

async def is_admin(client: Client, message: types.Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        return True
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.CREATOR]:
            bot_member = await client.get_chat_member(message.chat.id, client.me.id)
            return bot_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.CREATOR] and bot_member.can_pin_messages
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке админ-прав в чате {message.chat.id}: {e}")
        return False

async def check_bot_pin_rights(client: Client, message: types.Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        return True
    try:
        bot_member = await client.get_chat_member(message.chat.id, client.me.id)
        if not (bot_member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.CREATOR] and bot_member.can_pin_messages):
            await message.reply_text("Бот не имеет прав администратора для закрепления/открепления сообщений. Пожалуйста, выдайте ему эти права.")
            return False
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке прав бота на закрепление в чате {message.chat.id}: {e}")
        await message.reply_text("Произошла ошибка при проверке прав бота. Пожалуйста, убедитесь, что бот является администратором.")
        return False


@app.on_message(filters.command("start", prefixes=["/", "!"]) & filters.group)
async def start_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Достигнуто максимальное количество активных групп ({MAX_GROUPS}). Не могу начать сбор в этой группе.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, и бот должен иметь права на закрепление сообщений.")
        return

    if current_group_data["collection_active"]:
        await message.reply_text("Сбор участников уже запущен.")
        return

    current_group_data["collection_active"] = True
    await message.reply_text("Сбор участников начат. \nДобавьте 2х человек и отправьте свой @username.")
    logger.info(f"Сбор начат для чата: {chat_id}")
    save_group_data()

@app.on_message(filters.command("stop", prefixes=["/", "!"]) & filters.group)
async def stop_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, и бот должен иметь права на закрепление сообщений.")
        return
    
    if not current_group_data["collection_active"]:
        await message.reply_text("Сбор участников не активен.")
        return

    current_group_data["collection_active"] = False
    await message.reply_text("Сбор участников остановлен.")
    logger.info(f"Сбор остановлен для чата: {chat_id}")
    save_group_data()

@app.on_message(filters.command("list", prefixes=["/", "!"]) & filters.group)
async def list_participants_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await check_bot_pin_rights(client, message):
        return 

    participants = current_group_data["participants"]
    if participants:
        text = "<b>Список участников:</b>\n"
        for i, participant_entry in enumerate(participants, 1):
            username = participant_entry['username']
            user_id = participant_entry['user_id']
            if user_id != 0:
                text += f"✨ <b>{i}.</b> <a href='tg://user?id={user_id}'>{username}</a>\n"
            else:
                text += f"✨ <b>{i}.</b> {username}\n"
    else:
        text = "Список пока пуст."
    
    sent_message = await message.reply_text(text)
    logger.info(f"Список участников выведен для чата: {chat_id}. Message ID: {sent_message.id}")

    if current_group_data["last_pinned_message_id"]:
        try:
            await client.unpin_chat_message(chat_id=chat_id, message_id=current_group_data["last_pinned_message_id"])
            logger.info(f"Предыдущее закрепленное сообщение (ID: {current_group_data['last_pinned_message_id']}) откреплено в чате: {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка при откреплении предыдущего сообщения (ID: {current_group_data['last_pinned_message_id']}) в чате {chat_id}: {e}")

    try:
        await client.pin_chat_message(chat_id=chat_id, message_id=sent_message.id, disable_notification=True)
        current_group_data["last_pinned_message_id"] = sent_message.id
        logger.info(f"Новое сообщение (ID: {sent_message.id}) закреплено в чате: {chat_id}")
        save_group_data()
    except Exception as e:
        logger.error(f"Ошибка при закреплении нового сообщения (ID: {sent_message.id}) в чате {chat_id}: {e}")
        await message.reply_text("Не удалось закрепить сообщение. Убедитесь, что у бота есть права администратора для закрепления сообщений.")

@app.on_message(filters.command("reset_game", prefixes=["/", "!"]) & filters.group)
async def reset_game_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, и бот должен иметь права на закрепление сообщений.")
        return
    
    if await check_bot_pin_rights(client, message):
        if current_group_data["last_pinned_message_id"]:
            try:
                await client.unpin_chat_message(chat_id=chat_id, message_id=current_group_data["last_pinned_message_id"])
                logger.warning(f"Предыдущее закрепленное сообщение (ID: {current_group_data['last_pinned_message_id']}) откреплено при сбросе в чате: {chat_id}")
            except Exception as e:
                logger.warning(f"Не удалось открепить предыдущее сообщение при сбросе игры в чате {chat_id}: {e}")
        
    current_group_data["user_data"] = {}
    current_group_data["participants"] = []
    current_group_data["collection_active"] = False
    current_group_data["last_pinned_message_id"] = None
    await message.reply_text("Данные игры были успешно сброшены. Сбор участников остановлен.")
    logger.info(f"Данные игры сброшены для чата: {chat_id}")
    save_group_data()

@app.on_message(filters.new_chat_members & filters.group)
async def handle_new_members(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None or not current_group_data["collection_active"]:
        return

    inviter = message.from_user
    inviter_id = inviter.id
    new_users = message.new_chat_members

    if any(user.id == inviter_id for user in new_users):
        logger.info(f"Обнаружен самостоятельный вход пользователя {inviter_id} в чате {chat_id}. Игнорируется для подсчета приглашений.")
        return

    user_data = current_group_data["user_data"]
    if inviter_id not in user_data:
        user_data[inviter_id] = {"invites": 0, "username": "", "invited_user_ids": set()}

    added_this_time = 0
    for new_user in new_users:
        if new_user.is_bot:
            continue

        if new_user.id not in user_data[inviter_id]["invited_user_ids"]:
            user_data[inviter_id]["invited_user_ids"].add(new_user.id)
            added_this_time += 1
            logger.info(f"Пользователь {new_user.id} добавлен {inviter_id} в чате {chat_id}. Уникальное приглашение.")
        else:
            await message.reply_text(
                f"{full_name(inviter)}, пользователь {full_name(new_user)} уже был добавлен вами ранее. Не будет засчитан повторно."
            )
            logger.info(f"Пользователь {new_user.id} уже добавлен {inviter_id} в чате {chat_id}. Пропуск.")

    if added_this_time > 0:
        user_data[inviter_id]["invites"] += added_this_time
        invites = user_data[inviter_id]["invites"]
        save_group_data()

        is_inviter_in_participants = False
        for participant_entry in current_group_data["participants"]:
            if participant_entry["user_id"] == inviter_id:
                is_inviter_in_participants = True
                break

        if is_inviter_in_participants:
            await message.reply_text(
                f"Вы уже в списке, не нужно добавлять участников. Всего добавлено: {invites}."
            )
        elif invites < 2:
            await message.reply_text(
                f"{full_name(inviter)}, вы добавили {added_this_time} уникального(ых) участника(ов). Всего добавлено: {invites}. Добавьте еще!"
            )
        else:
            await message.reply_text(
                f"{full_name(inviter)}, вы уже выполнили условия. Всего добавлено: {invites}. Теперь вы можете отправить свой @username."
            )
        logger.info(f"Пригласивший {inviter_id} в чате {chat_id} теперь имеет {invites} приглашений.")

@app.on_message(filters.text & filters.regex(r"^@\w+$") & filters.group)
async def handle_username(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None or not current_group_data["collection_active"]:
        return

    user = message.from_user
    user_id = user.id
    text = message.text.strip()

    user_data = current_group_data["user_data"]
    participants = current_group_data["participants"]

    if user_id not in user_data:
        user_data[user_id] = {"invites": 0, "username": "", "invited_user_ids": set()}
    
    invites = user_data[user_id]["invites"]

    for participant_entry in participants:
        if participant_entry["user_id"] == user_id:
            await message.reply_text(
                f"Вы уже в списке участников с username: {participant_entry['username']}."
                "\nЕсли хотите изменить свой username, обратитесь к администратору."
            )
            logger.info(f"Пользователь {user_id} в чате {chat_id} попытался повторно зарегистрироваться. Уже в списке.")
            return

    for participant_entry in participants:
        if participant_entry["username"].lower() == text.lower():
            await message.reply_text(
                f"Username '{text}' уже занят другим участником. Пожалуйста, отправьте свой уникальный username, который вы используете."
            )
            logger.warning(f"Username '{text}' отправленный пользователем {user_id} в чате {chat_id} уже занят.")
            return
            
    if user_data[user_id].get("username") and user_data[user_id]["username"].lower() != text.lower():
        await message.reply_text(
            f"Вы уже отправляли username: {user_data[user_id]['username']}. "
            "Чтобы изменить его, обратитесь к администратору."
        )
        logger.info(f"Пользователь {user_id} в чате {chat_id} попытался изменить свой username с '{user_data[user_id]['username']}' на '{text}'.")
        return

    if invites < 2:
        await message.reply_text(
            f"Вы добавили меньше 2х уникальных участников ({invites} из 2). Добавьте ещё, прежде чем отправить свой @username!"
        )
        logger.info(f"Пользователь {user_id} ({text}) в чате {chat_id} попытался отправить username, но имеет только {invites} приглашений. Отклонено.")
        return

    user_data[user_id]["username"] = text
    participants.append({"user_id": user_id, "username": text})
    await message.reply_text("Вы успешно добавлены в список участников!")
    logger.info(f"Пользователь {user_id} ({text}) добавлен в список участников в чате {chat_id}.")
    save_group_data()
    
    await list_participants_command(client, message)

@app.on_message(filters.command("add_to_list", prefixes=["/", "!"]) & filters.group)
async def add_to_list_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    logger.info(f"Получена команда /add_to_list от пользователя {user.id} ({full_name(user)}) в чате {chat_id}.")

    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        logger.error(f"Попытка использовать /add_to_list в чате {chat_id}, но данные группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, и бот должен иметь права на закрепление сообщений.")
        return
    
    args = message.command
    if len(args) < 2:
        await message.reply_text("Пожалуйста, укажите один или несколько username для добавления. Пример: /add_to_list @username1 @username2")
        logger.info(f"Администратор {user.id} в чате {chat_id} использовал /add_to_list без аргументов.")
        return

    success_count = 0
    failed_usernames = []
    
    existing_usernames_in_participants = {p['username'].lower() for p in current_group_data['participants']}
    
    for arg_username in args[1:]:
        target_username = arg_username.strip()
        if not target_username.startswith("@"):
            target_username = "@" + target_username
            
        if target_username.lower() in existing_usernames_in_participants:
            failed_usernames.append(f"{target_username} (уже в списке)")
            logger.info(f"Администратор {user.id} в чате {chat_id} попытался добавить '{target_username}', но он уже в списке.")
            continue

        target_user_id = 0
        
        found_user_id = None
        for uid, data in current_group_data["user_data"].items():
            if data.get("username", "").lower() == target_username.lower():
                found_user_id = uid
                break
        
        if found_user_id:
            target_user_id = found_user_id
        else:
            logger.info(f"Не найден user_id для '{target_username}' в user_data. Будет использован ID по умолчанию (0).")

        new_participant_entry = {"user_id": target_user_id, "username": target_username}
        current_group_data["participants"].append(new_participant_entry)
        
        if target_user_id not in current_group_data["user_data"]:
            current_group_data["user_data"][target_user_id] = {
                "invites": 2,
                "username": target_username,
                "invited_user_ids": set()
            }
        else:
            current_group_data["user_data"][target_user_id]["username"] = target_username
            if current_group_data["user_data"][target_user_id]["invites"] < 2:
                current_group_data["user_data"][target_user_id]["invites"] = 2
        
        success_count += 1
        logger.info(f"Администратор {user.id} в чате {chat_id} вручную добавил '{target_username}' в список.")

    save_group_data()
    
    response_messages = []
    if success_count > 0:
        response_messages.append(f"Успешно добавлено {success_count} участник(ов) в список.")
    if failed_usernames:
        response_messages.append(f"Не удалось добавить: {', '.join(failed_usernames)}.")
    
    if not response_messages:
        await message.reply_text("Не удалось обработать ни одного username.")
    else:
        await message.reply_text("\n".join(response_messages))
    
    if success_count > 0:
        await list_participants_command(client, message)

@app.on_message(filters.command("remove_from_list", prefixes=["/", "!"]) & filters.group)
async def remove_from_list_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    logger.info(f"Получена команда /remove_from_list от пользователя {user.id} ({full_name(user)}) в чате {chat_id}.")

    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        logger.error(f"Попытка использовать /remove_from_list в чате {chat_id}, но данные группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, и бот должен иметь права на закрепление сообщений.")
        return
    
    args = message.command
    if len(args) < 2:
        await message.reply_text("Пожалуйста, укажите один или несколько username для удаления. Пример: /remove_from_list @username1 @username2")
        logger.info(f"Администратор {user.id} в чате {chat_id} использовал /remove_from_list без аргументов.")
        return

    success_count = 0
    failed_usernames = []
    
    for arg_username in args[1:]:
        target_username = arg_username.strip()
        if not target_username.startswith("@"):
            target_username = "@" + target_username
            
        participants = current_group_data["participants"]
        user_data = current_group_data["user_data"]
        
        found_index = -1
        found_user_id = None
        for i, participant_entry in enumerate(participants):
            if participant_entry["username"].lower() == target_username.lower():
                found_index = i
                found_user_id = participant_entry["user_id"]
                break

        if found_index != -1:
            removed_entry = participants.pop(found_index)
            
            if found_user_id and found_user_id in user_data:
                del user_data[found_user_id]
                logger.info(f"Данные пользователя {found_user_id} также очищены из user_data.")
            elif found_user_id == 0:
                user_id_to_clear = None
                for uid, data in user_data.items():
                    if data.get("username", "").lower() == target_username.lower():
                        user_id_to_clear = uid
                        break
                if user_id_to_clear:
                    del user_data[user_id_to_clear]
                    logger.info(f"Данные вручную добавленного пользователя (ID {user_id_to_clear} в user_data) очищены.")
            
            success_count += 1
            logger.info(f"Администратор {user.id} в чате {chat_id} вручную удалил '{target_username}' из списка.")
        else:
            failed_usernames.append(target_username)
            logger.info(f"Администратор {user.id} в чате {chat_id} попытался удалить '{target_username}', но он не найден.")
    
    save_group_data()

    response_messages = []
    if success_count > 0:
        response_messages.append(f"Успешно удалено {success_count} участник(ов) из списка.")
    if failed_usernames:
        response_messages.append(f"Не удалось удалить: {', '.join(failed_usernames)} (не найдены в списке).")

    if not response_messages:
        await message.reply_text("Не удалось обработать ни одного username.")
    else:
        await message.reply_text("\n".join(response_messages))

    if success_count > 0:
        await list_participants_command(client, message)

@app.on_message(filters.command("caller", prefixes=["/", "!"]) & filters.group)
async def caller_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам.")
        return
    
    all_members = []
    async for member in client.get_chat_members(chat_id):
        if member.user and not member.user.is_bot and not member.user.is_deleted:
            all_members.append(member.user)
    
    if not all_members:
        await message.reply_text("В чате нет пользователей, которых можно было бы позвать.")
        return

    message_parts = ["📢 *Время для новых участников!*", "\n"]
    
    chunk_size = 10
    emojis = await get_emojis()
    for i in range(0, len(all_members), chunk_size):
        chunk = all_members[i:i + chunk_size]
        current_chunk_mentions = []
        for user_obj in chunk:
            mention_string = f"<a href='tg://user?id={user_obj.id}'>{random.choice(emojis)}</a>"
            current_chunk_mentions.append(mention_string)
        
        await message.reply_text(" ".join(current_chunk_mentions), parse_mode=enums.ParseMode.HTML)
        await asyncio.sleep(0.1)

    await message.reply_text("_Присоединяйтесь к списку!_")
    logger.info(f"Зазывала вызван в чате {chat_id}, позвано всех доступных участников.")


@app.on_message(filters.command("random_winner", prefixes=["/", "!"]) & filters.group)
async def randomize_winner_command(client: Client, message: types.Message):
    chat_id = message.chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(client, message):
        await message.reply_text("Команда доступна только администраторам, так как это розыгрыш.")
        return
    
    participants = current_group_data["participants"]
    if not participants:
        await message.reply_text("Список участников пуст. Нет никого для розыгрыша.")
        return

    if len(participants) < 2:
        await message.reply_text("Для розыгрыша нужно как минимум 2 участника.")
        return
    
    winner_entry = random.choice(participants)
    winner_username = winner_entry['username']
    winner_user_id = winner_entry['user_id']

    if winner_user_id != 0:
        winner_text = f"🎉 *Поздравляем победителя:* <a href='tg://user?id={winner_user_id}'>{winner_username}</a> 🎉"
    else:
        winner_text = f"🎉 *Поздравляем победителя:* {winner_username} 🎉"
    
    await message.reply_text(winner_text, parse_mode=enums.ParseMode.HTML)
    logger.info(f"В чате {chat_id} выбран победитель: {winner_username} (ID: {winner_user_id}).")

async def main():
    load_group_data()
    logger.info("Запуск бота Pyrogram...")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())