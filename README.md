# Inspirational Feed (DE)

Dieses Repository erzeugt einmal täglich einen deutschsprachigen Kurzartikel rund um Persönlichkeitsentwicklung, Minimalismus, Frugalismus und Investieren. Die Inhalte werden in eine `feed.xml` geschrieben, die sich als RSS-Feed abrufen lässt.

## Funktionsweise

- **Täglich** erstellt das Skript `scripts/generate_item.py` einen Artikel (150–200 Wörter) über die OpenAI-API oder greift bei Problemen auf lokale Fallback-Texte zurück.
- **Themenrotation**: Entweder über die Umgebungsvariable `TOPICS` (kommagetrennte Stichwörter) oder über Standardthemen aus `DEFAULT_TOPICS`.
- **RSS-Pflege**: `scripts/update_feed.py` pflegt den RSS-Feed gemäß RSS 2.0, begrenzt auf `MAX_ITEMS` Einträge.
- **Automatisierung**: GitHub Actions (`.github/workflows/rss.yml`) laufen täglich gegen 07:05 Uhr Europa/Berlin und können manuell gestartet werden.

## Einrichtung

1. **Repository erstellen**
   - Dieses Projekt in ein neues Repository (z. B. `inspirational-feed`) kopieren.
   - Alle Dateien committen und auf die `main`-Branch pushen.

2. **GitHub Pages aktivieren**
   - Unter *Settings → Pages* die `main`-Branch (Root) auswählen.
   - Nach dem Deployment ist der Feed unter  
     `https://{GH_USER}.github.io/{REPO_NAME}/feed.xml` erreichbar.

3. **GitHub Actions konfigurieren**
   - Secret `OPENAI_API_KEY` hinzufügen (OpenAI API-Schlüssel).
   - Optional GitHub Actions → Variables setzen:
     - `MODEL` (Standard: `gpt-4o-mini`)
     - `FEED_TITLE`
     - `FEED_LINK`
     - `FEED_DESC`
     - `MAX_ITEMS` (Standard 60)
     - `DEFAULT_TOPICS` (Standard: `Minimalismus,Selbstentwicklung,Frugalismus,Investieren`)
     - `TOPICS` (optional, überschreibt Rotation)

4. **Kostenhinweis**
   - Pro Tag wird ein einzelner API-Call durchgeführt (geringe Kosten im Mikro-Cent-Bereich, abhängig vom Modell).

## Troubleshooting

- **Fallback-Artikel**: Bei API-Fehlern oder ungültigen Antworten nutzt das Skript Inhalte aus `data/fallback.json`.
- **403 bei Pages**: Prüfen, ob Pages auf der `main`-Branch aktiviert ist.
- **Keine neuen Einträge**: Action-Logs prüfen, API-Key und Variablen kontrollieren.

## Lizenz

MIT – siehe `LICENSE`.
