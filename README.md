# CS 145  - Group 19 - Firebridge Server Code

This repository contains the code used for the **FASTAPI Server** used to connect allow the Portalet Hardware to connect to the Firebase database. This connection is primarily conducted via **HTTP requests** made to the server hosted on Render


## Locally Testing the Server
1. Use the following command as the start command:

    ```shell
    uvicorn main:app --host 0.0.0.0 --port $PORT
    ```
2. The outputted URL will be the endpoint where test HTTP requests can be sent.
