import logging
import nest_asyncio
import asyncio

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

TOKEN = "7622381294:AAFE-gak873KscvFdmkIP-vadwiUefzytrw"

group_data = {}
MAX_GROUPS = 2

def get_group_data(chat_id):
    if chat_id not in group_data:
        if len(group_data) >= MAX_GROUPS:
            logging.warning(f"Превышено максимальное количество групп ({MAX_GROUPS}). Невозможно инициализировать данные для чата: {chat_id}")
            return None
        group_data[chat_id] = {
            "collection_active": False,
            "user_data": {},
            "participants": []
        }
        logging.info(f"Инициализированы данные для нового чата: {chat_id}. Всего активных групп: {len(group_data)}")
    return group_data[chat_id]

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return True
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return update.effective_user.id in [admin.user.id for admin in admins]
    except Exception as e:
        logging.error(f"Ошибка при проверке админ-прав в чате {update.effective_chat.id}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Достигнуто максимальное количество активных групп ({MAX_GROUPS}). Не могу начать сбор в этой группе.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    if current_group_data["collection_active"]:
        await update.message.reply_text("Сбор участников уже запущен.")
        return

    current_group_data["collection_active"] = True
    await update.message.reply_text("Сбор участников начат. \nДобавьте 2х человек и отправьте свой @username.")
    logging.info(f"Сбор начат для чата: {chat_id}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Команда доступна только администраторам.")
        return
    
    if not current_group_data["collection_active"]:
        await update.message.reply_text("Сбор участников не активен.")
        return

    current_group_data["collection_active"] = False
    await update.message.reply_text("Сбор участников остановлен.")
    logging.info(f"Сбор остановлен для чата: {chat_id}")

async def list_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
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
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("Список пока пуст.")
    logging.info(f"Список участников выведен для чата: {chat_id}")

async def reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Команда доступна только администраторам.")
        return

    current_group_data["user_data"] = {}
    current_group_data["participants"] = []
    current_group_data["collection_active"] = False
    await update.message.reply_text("Данные игры были успешно сброшены. Сбор участников остановлен.")
    logging.info(f"Данные игры сброшены для чата: {chat_id}")

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None or not current_group_data["collection_active"]:
        return

    inviter = update.message.from_user
    inviter_id = inviter.id
    new_users = update.message.new_chat_members

    if any(user.id == inviter_id for user in new_users):
        logging.info(f"Обнаружен самостоятельный вход пользователя {inviter_id} в чате {chat_id}. Игнорируется для подсчета приглашений.")
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
            logging.info(f"Пользователь {new_user.id} добавлен {inviter_id} в чате {chat_id}. Уникальное приглашение.")
        else:
            await update.message.reply_text(
                f"{inviter.full_name}, пользователь {new_user.full_name} уже был добавлен вами ранее. Не будет засчитан повторно."
            )
            logging.info(f"Пользователь {new_user.id} уже добавлен {inviter_id} в чате {chat_id}. Пропуск.")

    user_data[inviter_id]["invites"] += added_this_time
    invites = user_data[inviter_id]["invites"]

    is_inviter_in_participants = False
    for participant_entry in current_group_data["participants"]:
        if participant_entry["user_id"] == inviter_id:
            is_inviter_in_participants = True
            break

    if added_this_time > 0:
        if is_inviter_in_participants:
            await update.message.reply_text(
                f"Вы уже в списке, не нужно добавлять участников. Всего добавлено: {invites}."
            )
        elif invites < 2:
            await update.message.reply_text(
                f"{inviter.full_name}, вы добавили {added_this_time} уникального(ых) участника(ов). Всего добавлено: {invites}. Добавьте еще!"
            )
        else:
            await update.message.reply_text(
                f"{inviter.full_name}, вы уже выполнили условия. Всего добавлено: {invites}. Теперь вы можете отправить свой @username."
            )
    logging.info(f"Пригласивший {inviter_id} в чате {chat_id} теперь имеет {invites} приглашений.")

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_group_data = get_group_data(chat_id)

    if current_group_data is None or not current_group_data["collection_active"]:
        return

    user = update.message.from_user
    user_id = user.id
    text = update.message.text.strip()

    if not text.startswith("@"):
        logging.info(f"Получен не-username текст '{text}' от {user_id} в чате {chat_id}.")
        return

    user_data = current_group_data["user_data"]
    participants = current_group_data["participants"]

    if user_id not in user_data:
        user_data[user_id] = {"invites": 0, "username": "", "invited_user_ids": set()}
    
    invites = user_data[user_id]["invites"]

    for participant_entry in participants:
        if participant_entry["user_id"] == user_id:
            await update.message.reply_text(
                f"Вы уже в списке участников с username: {participant_entry['username']}."
                "\nЕсли хотите изменить свой username, обратитесь к администратору."
            )
            logging.info(f"Пользователь {user_id} в чате {chat_id} попытался повторно зарегистрироваться. Уже в списке.")
            return

    for participant_entry in participants:
        if participant_entry["username"].lower() == text.lower():
            await update.message.reply_text(
                f"Username '{text}' уже занят другим участником. Пожалуйста, отправьте свой уникальный username, который вы используете."
            )
            logging.warning(f"Username '{text}' отправленный пользователем {user_id} в чате {chat_id} уже занят.")
            return
            
    if user_data[user_id]["username"] and user_data[user_id]["username"].lower() != text.lower():
        await update.message.reply_text(
            f"Вы уже отправляли username: {user_data[user_id]['username']}. "
            "Чтобы изменить его, обратитесь к администратору."
        )
        logging.info(f"Пользователь {user_id} в чате {chat_id} попытался изменить свой username с '{user_data[user_id]['username']}' на '{text}'.")
        return

    if invites < 2:
        await update.message.reply_text(
            f"Вы добавили меньше 2х уникальных участников ({invites} из 2). Добавьте ещё, прежде чем отправить свой @username!"
        )
        logging.info(f"Пользователь {user_id} ({text}) в чате {chat_id} попытался отправить username, но имеет только {invites} приглашений. Отклонено.")
        return

    user_data[user_id]["username"] = text
    participants.append({"user_id": user_id, "username": text})
    await update.message.reply_text("Вы успешно добавлены в список участников!")
    logging.info(f"Пользователь {user_id} ({text}) добавлен в список участников в чате {chat_id}.")


async def add_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    logging.info(f"Получена команда /add_to_list от пользователя {user.id} ({user.full_name}) в чате {chat_id}.")

    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        logging.error(f"Попытка использовать /add_to_list в чате {chat_id}, но данные группы не инициализированы.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Команда доступна только администраторам.")
        logging.warning(f"Пользователь {user.id} попытался использовать /add_to_list без админ-прав в чате {chat_id}.")
        return
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите один или несколько username для добавления. Пример: `/add_to_list @username1 @username2`")
        logging.info(f"Администратор {user.id} в чате {chat_id} использовал /add_to_list без аргументов.")
        return

    success_count = 0
    failed_usernames = []

    for arg_username in context.args:
        target_username = arg_username.strip()
        if not target_username.startswith("@"):
            target_username = "@" + target_username
            
        participants = current_group_data["participants"]
        
        is_already_in_list = False
        for participant_entry in participants:
            if participant_entry["username"].lower() == target_username.lower():
                is_already_in_list = True
                break

        if is_already_in_list:
            failed_usernames.append(f"{target_username} (уже в списке)")
            logging.info(f"Администратор {user.id} в чате {chat_id} попытался добавить '{target_username}', но он уже в списке.")
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
            logging.info(f"Не найден user_id для '{target_username}' в user_data. Будет использован ID по умолчанию (0).")

        new_participant_entry = {"user_id": target_user_id, "username": target_username}
        participants.append(new_participant_entry)
        
        if target_user_id not in current_group_data["user_data"]:
            current_group_data["user_data"][target_user_id] = {"invites": 2, "username": target_username, "invited_user_ids": set()}
        else:
            current_group_data["user_data"][target_user_id]["username"] = target_username
            if current_group_data["user_data"][target_user_id]["invites"] < 2:
                current_group_data["user_data"][target_user_id]["invites"] = 2
        
        success_count += 1
        logging.info(f"Администратор {user.id} в чате {chat_id} вручную добавил '{target_username}' в список.")

    response_messages = []
    if success_count > 0:
        response_messages.append(f"Успешно добавлено {success_count} участник(ов) в список.")
    if failed_usernames:
        response_messages.append(f"Не удалось добавить: {', '.join(failed_usernames)}.")
    
    if not response_messages:
        await update.message.reply_text("Не удалось обработать ни одного username.")
    else:
        await update.message.reply_text("\n".join(response_messages))


async def remove_from_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    logging.info(f"Получена команда /remove_from_list от пользователя {user.id} ({user.full_name}) в чате {chat_id}.")

    current_group_data = get_group_data(chat_id)

    if current_group_data is None:
        await update.message.reply_text(f"Ошибка: данные для этой группы не инициализированы.")
        logging.error(f"Попытка использовать /remove_from_list в чате {chat_id}, но данные группы не инициализированы.")
        return

    if not await is_admin(update, context):
        await update.message.reply_text("Команда доступна только администраторам.")
        logging.warning(f"Пользователь {user.id} попытался использовать /remove_from_list без админ-прав в чате {chat_id}.")
        return
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите один или несколько username для удаления. Пример: `/remove_from_list @username1 @username2`")
        logging.info(f"Администратор {user.id} в чате {chat_id} использовал /remove_from_list без аргументов.")
        return

    success_count = 0
    failed_usernames = []

    for arg_username in context.args:
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
                logging.info(f"Данные пользователя {found_user_id} также очищены из user_data.")
            elif found_user_id == 0:
                for uid, data in user_data.items():
                    if data.get("username", "").lower() == target_username.lower() and data.get("invites", 0) >= 2:
                        data["username"] = ""
                        data["invites"] = 0
                        data["invited_user_ids"] = set()
                        logging.info(f"Данные вручную добавленного пользователя (ID {uid} в user_data) обнулены.")
                        break
            success_count += 1
            logging.info(f"Администратор {user.id} в чате {chat_id} вручную удалил '{target_username}' из списка.")
        else:
            failed_usernames.append(target_username)
            logging.info(f"Администратор {user.id} в чате {chat_id} попытался удалить '{target_username}', но он не найден.")
    
    response_messages = []
    if success_count > 0:
        response_messages.append(f"Успешно удалено {success_count} участник(ов) из списка.")
    if failed_usernames:
        response_messages.append(f"Не удалось удалить: {', '.join(failed_usernames)} (не найдены в списке).")

    if not response_messages:
        await update.message.reply_text("Не удалось обработать ни одного username.")
    else:
        await update.message.reply_text("\n".join(response_messages))


async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Запустить сбор участников (только админы)"),
        BotCommand("stop", "Остановить сбор (только админы)"),
        BotCommand("list", "Показать список участников (всем)"),
        BotCommand("reset_game", "Сбросить данные игры (только админы)"),
        BotCommand("add_to_list", "Вручную добавить username(ы) в список (только админы)"),
        BotCommand("remove_from_list", "Вручную удалить username(ы) из списка (только админы)"),
    ]
    await application.bot.set_my_commands(commands)
    logging.info("Команды бота установлены.")

async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("list", list_participants))
    application.add_handler(CommandHandler("reset_game", reset_game))
    application.add_handler(CommandHandler("add_to_list", add_to_list))
    application.add_handler(CommandHandler("remove_from_list", remove_from_list))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_username))

    application.post_init = set_bot_commands

    logging.info("Бот запущен и готов к опросу...")
    await application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())