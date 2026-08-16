import time


class Diagnostics:


    def __init__(self):

        self.events=[]


    def log(
        self,
        name,
        data=None
    ):

        self.events.append(
            {
                "time":time.time(),
                "event":name,
                "data":data or {}
            }
        )


    def dump(self):

        return self.events