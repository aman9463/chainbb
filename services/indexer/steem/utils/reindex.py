from datetime import datetime, timedelta
from steem import Steem
from pymongo import MongoClient
from pprint import pprint
import collections
import json
import time
import sys
import os

# load config from json file
print('Reading config.json file')
with open('../config.json') as json_config_file:
  config = json.load(json_config_file)
print(config)

ns = os.environ['namespace'] if 'namespace' in os.environ else 'eostalk'

s = Steem(config['steemd_nodes'])
mongo = MongoClient(config['mongo_url'])

db = mongo[ns]
# db = mongo.forums

data = json.loads(sys.argv[1])

def update_forum(data):
    update = {
      '$set': data,
      '$unset': {
        'children': 1
      }
    }
    if 'parent' in data:
        parent = db.forums.find_one({'_id': data['parent']})
        update['$set'].update({
          'parent_name': parent['name']
        })
    else:
        data.pop('parent', None)
        data.pop('parent_name', None)
        update['$unset'].update({
          'parent': True,
          'parent_name': True,
        })
    query = {
        '_id': data['_id']
    }
    results = db.forums.update(query, update, upsert=True)
    if results['n'] == 1 and results['updatedExisting'] == False:
        pprint("[FORUM][REINDEXER] - Inserting new forum [" + data['_id'] + "]")
    if results['n'] == 1 and results['updatedExisting'] == True:
        pprint("[FORUM][REINDEXER] - Updating forum [" + data['_id'] + "]")

def update_posts(data):
    query = {}
    if 'tags' in data and len(data['tags']) > 0:
        query.update({'category': {'$in': data['tags']}})
    if 'accounts' in data and len(data['accounts']) > 0:
        query.update({'author': {'$in': data['accounts']}})
    sort = [("last_reply",-1),("created",-1)]
    results = db.posts.find(query).sort(sort).limit(1)
    for comment in results:
        query = {
            '_id': data['_id'],
        }
        updates = {
            'updated': comment['created'],
            'last_post': {
                'created': comment['created'],
                'author': comment['author'],
                'title': comment['title'],
                'url': comment['url']
            }
        }
        pprint("[FORUM][REINDEXER] - Updating latest post to [" + str(comment['_id']) + "]...")
        response = db.forums.update(query, {'$set': updates}, upsert=True)

def update_replies(data):
    query = {}
    if 'tags' in data and len(data['tags']) > 0:
        query.update({'category': {'$in': data['tags']}})
    if 'accounts' in data and len(data['accounts']) > 0:
        query.update({'author': {'$in': data['accounts']}})
    sort = [("last_reply",-1),("created",-1)]
    results = db.replies.find(query).sort(sort).limit(1)
    for comment in results:
        query = {
            '_id': data['_id'],
        }
        updates = {
            'updated': comment['created'],
            'last_reply': {
                'created': comment['created'],
                'author': comment['author'],
                'title': comment['root_title'],
                'url': comment['url']
            }
        }
        pprint("[FORUM][REINDEXER] - Updating latest reply to [" + str(comment['_id']) + "]...")
        db.forums.update(query, {'$set': updates}, upsert=True)

def update_parent(data):
    db.forums.update({
        '_id': data['parent'],
        'children._id': {'$ne': data['_id']}
    }, {
        '$addToSet': {
            'children': {
                '_id': data['_id'],
                'name': data['name']
            }
        }
    })

if __name__ == '__main__':
    pprint("[FORUM][REINDEXER] - Starting script...")
    #sys.stdout.flush()
    update_forum(data)
    update_posts(data)
    update_replies(data)
    if 'parent' in data:
        update_parent(data)
