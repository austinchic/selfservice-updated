#!/usr/bin/env python
from flask.ext.script import Manager
from app import main

manager = Manager(main)

if __name__ == '__main__':
    manager.run()
