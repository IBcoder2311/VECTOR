from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Users, Ideas, Responses, Events

"""
Базовые команды:
1. Пользователи — Users

Функция	               Что делает

create_user	           Создаёт пользователя при первом входе через MAX
get_user_by_id	       Находит пользователя по внутреннему ID
get_user_by_max_id	   Находит пользователя по ID в MAX
update_user	           Обновляет имя, описание, аватар, навыки, ссылки
delete_user	           На всякий случай

2. Идеи — Ideas

Функция	               Что делает

create_idea	           Создаёт идею от имени пользователя
get_idea_by_id         Получает одну идею
get_ideas	           Получает список идей для каталога
get_ideas_by_owner	   Получает идеи конкретного пользователя
update_idea	           Изменяет описание, роли, дедлайн и другие поля
delete_idea	           Удаляет идею
increment_idea_views   Увеличивает счётчик просмотров

3. Отклики — Responses

Функция	               Что делает

create_response	       Создаёт отклик на идею
get_response_by_id	   Получает конкретный отклик
get_responses_by_idea  Показывает отклики на идею её владельцу
get_responses_by_user  Показывает отклики пользователя
delete_response	       Удаляет отклик

4. Мероприятия — Events

Функция	               Что делает

create_event	       Создаёт мероприятие
get_event_by_id	       Получает одно мероприятие
get_events	           Получает список мероприятий
get_events_by_owner	   Получает мероприятия организации
update_event	       Изменяет мероприятие
delete_event	       Удаляет мероприятие

"""


# USERS


# IDEAS


# RESPONSES


# EVENTS