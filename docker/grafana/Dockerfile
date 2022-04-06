FROM grafana/grafana-oss

COPY datasource.yml /etc/grafana/provisioning/datasources/datasource.yml
COPY dashboard.yml /etc/grafana/provisioning/dashboards/datasource.yml

COPY dashboard.json /etc/dashboards/dashboard.json

EXPOSE 3000