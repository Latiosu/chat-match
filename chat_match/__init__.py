__version__ = '0.1.0'

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask
from flask_restful import Resource, Api, reqparse

from datetime import datetime, timezone
import random
import re
import string
import uuid
from uuid import UUID


# Use a service account
cred = credentials.Certificate('firebase-secret.json')
firebase_admin.initialize_app(cred)

db = firestore.client()
app = Flask(__name__)
api = Api(app)


class Graphs(Resource):
    """Graphs containing nodes and edges"""

    def get(self):
        graphs_ref = db.collection('graphs')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=False)
        args = parser.parse_args()
        graphId = args['graph_id']
        if graphId is not None and self.is_valid_graph_id(graphId):
            graph = graphs_ref.document(graphId).get()
            if graph.exists:
                return {'data': graph.to_dict()}, 200
            else:
                return {'message': f'No such graph with id {graphId}'}, 401
        else:
            query = graphs_ref.order_by('created').limit(50)
            res = {}
            count = 0
            for graph in query.stream():
                res[graph.id] = graph.to_dict()
            return {'data': res}, 200
    
    def post(self):
        graphs_ref = db.collection('graphs')
        parser = reqparse.RequestParser()
        parser.add_argument('names', required=True, help="names parameter required")
        args = parser.parse_args()
        names = self.filter_names(args['names'].split(','))

        # Generate graph identifier
        success = False
        attempt = 0
        graphId = None
        while not success and attempt < 3:
            graphId = self.generate_identifier()
            attempt += 1
            if not graphs_ref.document(graphId).get().exists:
                success = True
        if graphId is None:
            return {'message': f'Unable to generate graph, please try again later'}, 500

        # Build initial graph
        nodes = {}
        for name in names:
            nodes[name] = {'edges': []}
        graph = {
            'created': str(datetime.now(timezone.utc)),
            'events': [],
            'nodes': nodes
        }
        graphs_ref.document(graphId).set(graph)
        return {'graph_id': graphId}, 200
    
    def delete(self):
        graphs_ref = db.collection('graphs')
        events_ref = db.collection('events')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=True, help="graph_id parameter required")
        args = parser.parse_args()
        graphId = args['graph_id']

        if not self.is_valid_graph_id(graphId):
            return {'message': f'Invalid graph id {graphId}'}, 400
    
        graph = graphs_ref.document(graphId).get()
        if not graph.exists:
            return {'message': f'No such graph with id {graphId}'}, 404
        
        graphs_ref.document(graphId).delete()
        for event in events_ref.where('graph', '==', graphId).stream():
            event.delete()
        return {'message': f'Deleted graph and events with graph_id {graphId}'}, 200
    
    def is_valid_graph_id(self, graphId):
        cleaned = re.sub('[^A-Z]', '', graphId).strip()
        if len(cleaned) != 4:
            return False
        return True
    
    def filter_names(self, names):
        filtered_names = []
        for name in names:
            cleaned = re.sub('[^a-zA-Z0-9 ]', '', name).strip()
            if len(cleaned) > 0 and cleaned not in filtered_names:
                filtered_names.append(cleaned)
        return filtered_names
    
    def generate_identifier(self):
        return "".join(random.sample(list(string.ascii_uppercase), k=4))


class Events(Resource):
    """Instances of matching events"""

    def get(self):
        events_ref = db.collection('events')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=False)
        parser.add_argument('event_id', required=False)
        args = parser.parse_args()
        eventId = args['event_id']
        graphId = args['graph_id']
        if (eventId is not None and graphId is not None) \
            or (eventId is None and graphId is None):
            return {'message': f'One of either graph_id or event_id is required'}, 400
        elif eventId is not None and self.is_valid_event_id(eventId):
            event = events_ref.document(eventId).get()
            if event.exists:
                return {'data': event.to_dict()}, 200
            else:
                return {'message': f'No such event with id {eventId}'}, 401
        elif graphId is not None and self.is_valid_graph_id(graphId):
            query = events_ref.where('graph', '==', graphId).order_by('created')
            res = []
            count = 0
            for event in query.stream():
                count += 1
                res.append(event.to_dict())
            if count > 0:
                return {'data': res}, 200
            else:
                return {'message': f'No events under graph_id {graphId}'}, 401

    def post(self):
        graphs_ref = db.collection('graphs')
        events_ref = db.collection('events')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=True)
        args = parser.parse_args()
        graphId = args['graph_id']

        if not self.is_valid_graph_id(graphId):
            return {'message': f'Invalid graph id {graphId}'}, 400

        graph = graphs_ref.document(graphId).get()
        if not graph.exists:
            return {'message': f'No such graph with id {graphId}'}, 401

        # Compute changes and persist
        res = self.algorithm(graph)
        if res is None:
            return {'message': f'Unable to create event, please try again later'}, 500

        graphs_ref.document(graphId).set(res['graph'])
        events_ref.document(res['event_id']).set(res['event'])
        return {'data': res['event'].to_dict()}, 200

    def algorithm(self, graph, graphId):
        """Computes matches and returns updated graph + event"""
        nodes = []
        edges = set()
        new_named_edges = []
        event = {
            'graph': graphId,
            'created': str(datetime.now(timezone.utc)),
            'edges': []
        }

        # Parse input data
        for node in graph['nodes']:
            nodes.append(node['name'])
            for edge in node['edges']:
                edges.add(f'{node.key},{edge}' if node.key < edge else f'{edge},{node.key}')

        # for node in nodes:
            # TODO
            # 1. Find a new edge to not self
            

            # 2. Save to graph and event and named edge list
        
        

        return {'graph': graph, 'event_id': uuid.uuid4(), 'event': event}
    
    def is_valid_graph_id(self, graphId):
        cleaned = re.sub('[^A-Z]', '', graphId).strip()
        if len(cleaned) != 4:
            return False
        return True
    
    def is_valid_event_id(self, eventId):
        try:
            uuid_obj = UUID(eventId, version=4)
        except ValueError:
            return False
        return str(uuid_obj) == eventId


class Nodes(Resource):
    """Representation of a user in a graph"""

    def get(self):
        """Get node in graph"""
        # TODO: Implement
        pass

    def post(self):
        """Add node to graph"""
        # TODO: Implement
        pass

    def put(self):
        """Update node in graph"""
        # TODO: Implement
        pass
    
    def is_valid_graph_id(self, graphId):
        cleaned = re.sub('[^A-Z]', '', graphId).strip()
        if len(cleaned) != 4:
            return False
        return True


api.add_resource(Graphs, '/graphs')
api.add_resource(Events, '/events')
api.add_resource(Nodes, '/nodes')

if __name__ == '__main__':
    app.run()
