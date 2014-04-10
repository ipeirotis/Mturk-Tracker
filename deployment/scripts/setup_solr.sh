#!/bin/bash

MTURK_HOME="${MTURK:-/var/www/mturk}"
SOLR_VERSION="${SOLR_VERSION:-3.6.0}"
DL_TO=/tmp/%(project_name)s
FILE=solr.tgz
UPDATE=${UPDATE:-false}
SUCCESS_FILE="$MTURK_HOME/solr/.fabric_solr_install_success"

if [ ! -d "$DL_TO" ]; then
    mkdir "$DL_TO"
fi

if ([ ! -f "$DL_TO/$FILE" ] || $UPDATE );
then
    echo "Downloading solr"
    wget "https://archive.apache.org/dist/lucene/solr/$SOLR_VERSION/apache-solr-$SOLR_VERSION.tgz" -O "$DL_TO/$FILE"
    echo "Downloading PostgreSQL JDBC driver"
    wget "http://jdbc.postgresql.org/download/postgresql-9.1-902.jdbc4.jar" -O "$DL_TO/postgresql.jdbc4.jar"
    echo "Unpacking solr"
    tar -C "$DL_TO" --overwrite -xvzf "$DL_TO/$FILE"
else
    echo "Solr package found - skipping download."
fi

if ([ ! -f $SUCCESS_FILE ] || $UPDATE );
then
    echo "Installing solr"
    cp -rf "$DL_TO/apache-solr-$SOLR_VERSION/example/lib" "$MTURK_HOME/solr"
    cp "$DL_TO/apache-solr-$SOLR_VERSION/example/start.jar" "$MTURK_HOME/solr"
    cp -rf "$DL_TO/apache-solr-$SOLR_VERSION/example/webapps" "$MTURK_HOME/solr"
    cp -rf "$DL_TO/apache-solr-$SOLR_VERSION/dist" "$MTURK_HOME/solr"
    cp "$DL_TO/postgresql.jdbc4.jar" "$MTURK_HOME/solr/dist/"
    touch $SUCCESS_FILE
else
    echo "Solr already installed - skipping install."
fi
