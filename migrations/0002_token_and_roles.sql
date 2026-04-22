insert into roles (title, permissions) values ('user', 31), ('moderator', 255), ('admin', 2147483647);

create table tokens(
    user_id integer primary key references users(id) on delete cascade,
    access_token uuid default gen_random_uuid(),
    valid_until timestamptz,
);

create function get_or_create_user_token(user_id integer) returns uuid
    language plpgsql
as
$fun$
DECLARE
token uuid;
begin
    select access_token from tokens at where at.user_id=get_or_create_user_token.user_id into token;
    if token is null then
        token = gen_random_uuid();
        insert into tokens(user_id, access_token, valid_until) values (get_or_create_user_token.user_id, token, now() + interval '7d');
    end if;
    return token;
end
$fun$;

