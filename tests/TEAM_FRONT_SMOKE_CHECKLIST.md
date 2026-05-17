# Team Front Smoke Checklist

1. Owner opens `/team`, sees tabs `Сотрудники` and `Клиенты`.
2. Owner invites member/client by email; new record appears with badge `Активен` or `Ожидает`.
3. Pending invite: open link `/team/accept?token=...` — preview, login/register, accept.
4. Owner grants project access; project card appears under member; grant modal shows «Уже имеют доступ».
5. Owner revokes project access; project card disappears.
6. Owner deletes member; confirm text mentions role and name/email.
7. At tariff limit, invite shows modal «Перейти к тарифам».
8. Member login: sidebar hides `Команда`, `Тарифы`, but `Интеграции` remains visible.
9. Client login: sidebar additionally hides `Интеграции`, `История`.
10. Member sees own projects + shared projects; Client sees only shared projects.
11. Owner sees team projects in `/api/team/projects` and in project selectors.
12. History: filter «Команда», actor email displayed, team actions have Russian labels.
