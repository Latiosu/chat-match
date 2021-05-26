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
        graph_id = args['graph_id']
        if graph_id is not None and self.is_valid_graph_id(graph_id):
            graph = graphs_ref.document(graph_id).get()
            if graph.exists:
                return {'data': graph.to_dict()}, 200
            else:
                return {'message': f'No such graph with id {graph_id}'}, 401
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
        graph_id = None
        while not success and attempt < 3:
            graph_id = self.generate_identifier()
            attempt += 1
            if not graphs_ref.document(graph_id).get().exists:
                success = True
        if graph_id is None:
            return {'message': f'Unable to generate graph, please try again later'}, 500

        # Build initial graph
        graph = {
            'graph_id': graph_id,
            'created': str(datetime.now(timezone.utc)),
            'events': [],
            'nodes': [{'node_id': i, 'name': name, 'edges': []} for i, name in enumerate(names)]
        }
        graphs_ref.document(graph_id).set(graph)
        return {'graph_id': graph_id}, 200

    def delete(self):
        graphs_ref = db.collection('graphs')
        events_ref = db.collection('events')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=True, help="graph_id parameter required")
        args = parser.parse_args()
        graph_id = args['graph_id']

        if not self.is_valid_graph_id(graph_id):
            return {'message': f'Invalid graph id {graph_id}'}, 400

        graph = graphs_ref.document(graph_id).get()
        if not graph.exists:
            return {'message': f'No such graph with id {graph_id}'}, 404

        for event in events_ref.where('graph_id', '==', graph_id).stream():
            events_ref.document(event.to_dict()['event_id']).delete()
        graphs_ref.document(graph_id).delete()
        return {'message': f'Deleted graph and events with graph_id {graph_id}'}, 200

    def is_valid_graph_id(self, graph_id):
        cleaned = re.sub('[^A-Z]', '', graph_id).strip()
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
        parser.add_argument('event_id', required=False)
        parser.add_argument('graph_id', required=False)
        args = parser.parse_args()
        event_id = args['event_id']
        graph_id = args['graph_id']
        if (event_id is not None and graph_id is not None) \
            or (event_id is None and graph_id is None):
            return {'message': f'One of either graph_id or event_id is required'}, 400
        elif event_id is not None and self.is_valid_event_id(event_id):
            event = events_ref.document(event_id).get()
            if event.exists:
                return {'data': event.to_dict()}, 200
            else:
                return {'message': f'No such event with id {event_id}'}, 401
        elif graph_id is not None and self.is_valid_graph_id(graph_id):
            query = events_ref.where('graph_id', '==', graph_id).order_by('created')
            res = []
            for event in query.stream():
                res.append(event.to_dict())
            return {'data': res}, 200
        else:
            return {'message': f'Invalid graph_id or event_id given'}, 400

    def post(self):
        graphs_ref = db.collection('graphs')
        events_ref = db.collection('events')
        parser = reqparse.RequestParser()
        parser.add_argument('graph_id', required=True)
        args = parser.parse_args()
        graph_id = args['graph_id']

        if not self.is_valid_graph_id(graph_id):
            return {'message': f'Invalid graph id {graph_id}'}, 400

        graph = graphs_ref.document(graph_id).get()
        if not graph.exists:
            return {'message': f'No such graph with id {graph_id}'}, 401

        # Compute changes and persist
        res = self.algorithm(graph.to_dict(), graph_id)
        if res is None:
            return {'message': f'Insufficient nodes to match, at least 2 required'}, 401

        graphs_ref.document(graph_id).set(res['graph'])
        events_ref.document(str(res['event_id'])).set(res['event'])
        return {'data': res['event']}, 200

    def algorithm(self, graph, graph_id, match_odd=False):
        """Computes matches and returns updated graph + event."""
        N = len(graph['nodes'])
        if N < 2:
            return None

        # Parse input data
        matrix = [[False for i in range(N)] for j in range(N)]
        for nodeId, node in enumerate(graph['nodes']):
            matrix[nodeId][nodeId] = True # Ignore self
            for edge in node['edges']:
                matrix[nodeId][edge] = True # Undirected edge exists
                matrix[edge][nodeId] = True

        assigned = []
        edges = []
        # TODO: Handle matching odd number of nodes
        # Find and record new edges, one edge per node
        for nodeId, node in enumerate(graph['nodes']):
            if nodeId not in assigned:
                for otherId in range(0,N):
                    if otherId not in assigned and not matrix[nodeId][otherId]:
                        assigned.append(nodeId)
                        assigned.append(otherId)
                        edges.append({
                            'node_a': nodeId,
                            'node_b': otherId,
                            'name_a': node['name'],
                            'name_b': graph['nodes'][otherId]['name']
                        })
                        node['edges'].append(otherId)
                        graph['nodes'][otherId]['edges'].append(nodeId)
                        matrix[nodeId][otherId] = True
                        matrix[otherId][nodeId] = True
                        break

        event_id = str(uuid.uuid4())
        event = {
            'event_id': event_id,
            'graph_id': graph_id,
            'created': str(datetime.now(timezone.utc)),
            'edges': edges
        }
        graph['events'].append(event_id)
        return {'graph': graph, 'event_id': event_id, 'event': event}

    def is_valid_graph_id(self, graph_id):
        cleaned = re.sub('[^A-Z]', '', graph_id).strip()
        if len(cleaned) != 4:
            return False
        return True

    def is_valid_event_id(self, event_id):
        try:
            uuid_obj = UUID(event_id, version=4)
        except ValueError:
            return False
        return str(uuid_obj) == event_id


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

    def is_valid_graph_id(self, graph_id):
        cleaned = re.sub('[^A-Z]', '', graph_id).strip()
        if len(cleaned) != 4:
            return False
        return True


api.add_resource(Graphs, '/graphs')
api.add_resource(Events, '/events')
api.add_resource(Nodes, '/nodes')

if __name__ == '__main__':
    app.run()
