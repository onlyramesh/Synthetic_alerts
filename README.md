# Synthetic_alerts
This is one of the python scprit written for checking the health of few number of API's,where it check keep on checking the API whether it is up and running or not means status code must be 200.

If an API found not up means status code is not 200 it will send an alert to the slack channel by saying that "[name of API] id down with status code " And once the API is up and runnign script send another message to the slack channel by saying that "[NameofAPI] is up with the status code ".

And also it store all the details(what time which API was down and how many seconds and when it came up with the all the status code and Failure resons) in the mysq database.

Imported requests packages to check the status of a API.

Imported slack packages to send an alert to the slack channel.

