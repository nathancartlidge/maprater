# OW Map Rater
An attempt to discover the most painful overwatch map, alongside other data!

[Add to your server](https://discord.com/api/oauth2/authorize?client_id=1027923329333608458&permissions=277025695744&scope=bot%20applications.commands)

## Self-hosting
I have hosted the bot on a fly.io instance - with `flyctl` set up, the
following will deploy the discord bot

```shell
> fly launch
> fly volumes create maprater_data
> fly secrets set DISCORD_TOKEN=...
> fly deploy
```

Alternatively, you can run it as a docker container, although you may need to
change the data storage location (in `main.py`) to prevent issues

## Privacy
- The bot will only store the information required to register rankings:
  - Username
  - Server ID
  - Date / Time
  - Vote (Map, Role, Result, Sentiment)
- Data for a particular server can be requested at any time, using the `/data`
  command
- Data (for the bot linked above) is stored on EU-based fly.io instances, please refer to their privacy
  policy [here](https://fly.io/legal/privacy-policy/)