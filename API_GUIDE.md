Handleiding: API-Credentials Verkrijgen
Deze gids helpt je bij het verkrijgen van de benodigde API-credentials voor het publiceren naar Mastodon en Reddit. Volg deze stappen en voeg de verkregen waarden toe aan je .env bestand.
1. Mastodon
Voor Mastodon heb je de URL van je instance (server) en een Access Token nodig.
Log in op je Mastodon-account in de browser.
Navigeer naar Voorkeuren -> Ontwikkeling.
Klik op de knop "Nieuwe applicatie".
Applicatienaam: Geef een herkenbare naam, bijvoorbeeld VBR Publisher.
Redirect URI: Dit veld is verplicht maar is al correct ingevuld met urn:ietf:wg:oauth:2.0:oob. Je kunt deze waarde laten staan.
Rechten (Scopes): Zorg ervoor dat minimaal write:statuses is aangevinkt. Dit is vereist om berichten te kunnen plaatsen.
Klik op "Opslaan".
Je komt nu op de detailpagina van je nieuwe applicatie. Bovenaan zie je "Jouw toegangstoken". Dit is de sleutel die je nodig hebt.
Benodigde waarden voor .env:
MASTODON_API_BASE_URL: De URL van je Mastodon-server (bv. https://mastodon.social).
MASTODON_ACCESS_TOKEN: Het zojuist gegenereerde toegangstoken.
2. Reddit
Voor Reddit moet je een "script" applicatie aanmaken. Dit geeft je een Client ID en een Client Secret.
Log in op je Reddit-account.
Navigeer naar de app-voorkeuren: https://www.reddit.com/prefs/apps
Scrol naar beneden en klik op de knop "are you a developer? create an app...".
Name: Geef een unieke naam, bijvoorbeeld VBR_Publisher_Bot.
Type: Selecteer script. Dit is cruciaal.
Description: Een korte beschrijving (optioneel).
Redirect URI: Dit veld is verplicht. Vul hier een placeholder URL in, bijvoorbeeld http://localhost:8080. Deze URL wordt niet gebruikt door het script, maar is nodig om de app aan te maken.
Klik op "create app".
Je ziet nu je nieuwe app in de lijst.
De Client ID staat direct onder de naam van je app (een korte reeks tekens).
Het Client Secret is de waarde naast het label secret.
Benodigde waarden voor .env:
REDDIT_CLIENT_ID: De Client ID die je zojuist hebt gekregen.
REDDIT_CLIENT_SECRET: Het Client Secret dat je hebt gekregen.
REDDIT_USERNAME: Je Reddit-gebruikersnaam.
REDDIT_PASSWORD: Je Reddit-wachtwoord.
REDDIT_USER_AGENT: Een unieke string om je script te identificeren. Goede praktijk is een format zoals script:VBR_Publisher:v1.0 (by /u/JOUW_USERNAME). Vervang JOUW_USERNAME door je eigen Reddit-naam.
--- END OF FILE API_GUIDE.md ---
