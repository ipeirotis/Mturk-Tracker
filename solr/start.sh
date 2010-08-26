#!/bin/sh

SOLR_HOME="/var/www/mturk/solr"

for lib in $SOLR_HOME/lib/*.jar ; do
  LIBS="${LIBS}:$lib"
done

for lib in $SOLR_HOME/*.jar ; do
  LIBS="${LIBS}:$lib"
done

#-Dsolr.clustering.enabled=true
java -Xmx512m -Dfile.encoding=UTF-8 -cp $LIBS org.mortbay.start.Main
