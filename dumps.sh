neo4j stop
mkdir -p /data/dumps
neo4j-admin database dump neo4j --to-path=/data/dumps/
udocker export neo4j-primekg > container.tar