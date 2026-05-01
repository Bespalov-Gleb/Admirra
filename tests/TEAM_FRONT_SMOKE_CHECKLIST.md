# Team Front Smoke Checklist

1. Owner opens `/team`, sees tabs `Сотрудники` and `Клиенты`.
2. Owner invites member/client by email; new record appears with pending/active status.
3. Owner grants project access; project card appears under member.
4. Owner revokes project access; project card disappears.
5. Owner deletes member; member disappears from list.
6. Member login: sidebar hides `Команда`, `Тарифы`, but `Интеграции` remains visible.
7. Client login: sidebar additionally hides `Интеграции`, `История`.
8. Member sees own projects + shared projects; Client sees only shared projects.
9. Owner sees team projects in `/api/team/projects` and in project selectors.
