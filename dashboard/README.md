# Essentials+ Freelancer Dashboard

Separates Homer-Dashboard nach dem Vorbild von `dashboard.mantle-climbing.de`.

## Betrieb

Der Service `freelancer-dashboard` ist Bestandteil des Compose-Stacks im Repository-Root. Er bindet `dashboard/assets` schreibgeschützt unter `/www/assets` ein und hängt wie das Freelancer-Frontend am externen Docker-Netz `proxy_net`.

```bash
docker network inspect proxy_net >/dev/null 2>&1 || docker network create proxy_net
docker compose pull freelancer-dashboard
docker compose up -d freelancer-dashboard
docker compose ps freelancer-dashboard
```

Lokal ist Homer standardmäßig unter `http://<NUC-IP>:8081` erreichbar. Der Host-Port kann über `DASHBOARD_PORT` in `.env` geändert werden.

## Caddy

Der Reverse Proxy muss ebenfalls mit `proxy_net` verbunden sein. Beispiel aus `Caddyfile.example`:

```caddyfile
dashboard.itmitalles.de {
    reverse_proxy freelancer-dashboard:8080
}
```

Danach DNS für `dashboard.itmitalles.de` auf denselben öffentlichen Einstieg wie die übrigen NUC-Dienste legen und Caddy neu laden.

## Anpassen

- Kacheln, Gruppen und Farben: `assets/config.yml`
- Kleine visuelle Anpassungen: `assets/custom.css`
- Konfigurationsänderungen benötigen keinen Container-Neustart; Browser neu laden genügt.
- Keine Zugangsdaten oder Tokens in Homer ablegen: Die Konfiguration wird vollständig an den Browser ausgeliefert.

Die bekannten Arbeitslinks zeigen derzeit aus Kompatibilitätsgründen auf
`tracker.itmitalles.de`. Die interne URL ist keine sichtbare Produktbezeichnung.
Falls die App später auf eine andere Domain umzieht, alle Essentials+-URLs in
`assets/config.yml` gemeinsam ändern und Proxy/DNS extern verifizieren.
