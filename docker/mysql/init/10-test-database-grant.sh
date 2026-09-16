#!/bin/sh
# Lets the app user create and drop the database Django's test runner uses (test_<name>).
# Runs only when the MySQL data volume is first created. Calls the mysql client directly
# because the image may execute this file rather than source it (it does on Windows mounts).
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --protocol=socket -uroot <<EOSQL
GRANT ALL PRIVILEGES ON \`test_${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
EOSQL
