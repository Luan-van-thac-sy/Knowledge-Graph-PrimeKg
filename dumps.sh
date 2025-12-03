neo4j stop
mkdir -p /data/dumps
neo4j-admin database dump neo4j --to-path=/data/dumps/
udocker export neo4j-primekg > container.tar
neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/data/dumps \
  --overwrite-destination=true
