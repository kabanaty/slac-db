import collections.abc
import copy
import yaml
import yaml.constructor
import yaml.loader
import yaml.nodes

def read_dict(p):
    """Reads from YAML with a MultiDictLoader, such that:
    [foo, bar]:
        a: 0
        b: 1
    Becomes:
        {
            "foo": {"a": 0, "b": 1}
            "bar": {"a": 0, "b": 1}
        }
    Warning: The internal dictionary value is resolved
    immediately and not lazily. Self references are not
    supported.

    Args:
        p: Path to YAML.
    Returns:
        A dictionary from a YAML file.
    """
    with open(p, 'r') as r:
        return yaml.load(r, Loader=_MultiDictLoader)

class _MultiDictLoader(yaml.loader.SafeLoader):
    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.nodes.MappingNode):
            raise yaml.constructor.ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        for key_node, value_node in node.value:
            if isinstance(key_node, yaml.nodes.SequenceNode):
                key = self.construct_sequence(key_node, deep=deep)
                for k in key:
                    self._require_hashable(node, key_node, k)
                value = self.construct_object(value_node, deep=True)
                mapping.update({k: copy.deepcopy(value) for k in key})
            else:
                key = self.construct_object(key_node, deep=deep)
                self._require_hashable(node, key_node, key)
                value = self.construct_object(value_node, deep=deep)
                mapping[key] = value
        return mapping

    def _require_hashable(self, mapping_node, key_node, key):
        if not isinstance(key, collections.abc.Hashable):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", mapping_node.start_mark,
                "found unhashable key", key_node.start_mark)
