Установка

```docker run -d -e AGRAPH_SUPER_USER=test -e AGRAPH_SUPER_PASSWORD=xyzzy -p 10000-10035:10000-10035 --shm-size 1g --name agraph --restart=always franzinc/agraph```

```pip install -r requirements.txt```

Запуск 

```python gui.py```
