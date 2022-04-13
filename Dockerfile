FROM debian:9
ENV PBA_CONFIG "/pba/test-example.conf"

RUN apt-get update && apt-get install -y \
	python-twisted-bin \
	python-twisted-core

COPY ./ /pba/
WORKDIR /pba/
EXPOSE 8080
CMD /pba/pba -c $PBA_CONFIG
