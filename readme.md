## Jira+Tempo client

#### TODO
1. GUI
1. Start/stop the timers
1. Save timers data between sessions (store data with pickle)
1. Choose an issue to the timer (by summary or key)
1. Create issues
1. Make a transitions to the issues including required fields (i.e. tempo account)
1. Ability to resolve on log work

#### Instructions
1. Config creation
```python
from main import Config
config = Config()
config.url = 'http://your_jira_server:8080'
config.login = 'your_jira_login'
config.password = 'your_jira_pass'
config.save()
```
This creates the config.ini file into current directory