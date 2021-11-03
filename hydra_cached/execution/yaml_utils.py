from __future__ import annotations

from typing import Any, Optional, Type, List, Dict

import yaml
from omegaconf._utils import OmegaConfDumper
from yaml import SequenceNode, MappingNode, Node
from yaml.emitter import EmitterError


class ConfDumper(OmegaConfDumper):
    """
    This is an extended version of OmegaConfDumper
    that names anchors by their shortest path in the config.
    In addition, callables are never anchored (see ignore_aliases).
    """
    # These two strings have to be single characters! See their usage in prepare_anchor.
    anchor_path_sep = "."
    anchor_key_marker = "@"

    def prepare_anchor(self, anchor):
        if not anchor:
            raise EmitterError("anchor must not be empty")
        for ch in anchor:
            if not ('0' <= ch <= '9' or 'A' <= ch <= 'Z' or 'a' <= ch <= 'z' or ch in '-_'
                    or ch in [self.anchor_path_sep, self.anchor_key_marker]):
                raise EmitterError("invalid character %r in the anchor: %r"
                                   % (ch, anchor))
        return anchor

    def anchor_node(self, node: Node):
        node_paths = self.collect_paths(node=node, paths={}, current_path=[])
        for n in node_paths:
            all_paths = node_paths[n]
            # if there is only one path to the node, do not create an anchor
            if len(all_paths) == 1:
                self.anchors[n] = None
            else:
                shortest_path = sorted(all_paths, key=len)[0]
                self.anchors[n] = self.anchor_path_sep.join(shortest_path)

    def collect_paths(self, node: Node, paths: Dict[Node, List[List[str]]], current_path: Optional[List[str]] = None) \
            -> Dict[Node, List[List[str]]]:
        if node in paths:
            paths[node].append(current_path)
        else:
            paths[node] = [current_path]
            if isinstance(node, SequenceNode):
                for i, item in enumerate(node.value):
                    new_path = current_path + [f'{i}']
                    self.collect_paths(item, paths=paths, current_path=new_path)
            elif isinstance(node, MappingNode):
                for key, value in node.value:
                    # mark key with prefix character
                    _key = f'{self.anchor_key_marker}{key.value}'
                    assert _key not in [f'{k.value}' for k, v in node.value], \
                        f'key="{_key}" not allowed when key={key.value} is used'
                    self.collect_paths(key, paths=paths, current_path=current_path + [_key])
                    self.collect_paths(value, paths=paths, current_path=current_path + [f'{key.value}'])
        return paths

    def ignore_aliases(self, data):
        if super().ignore_aliases(data):
            return True

        if callable(data):
            return True

        return False


def get_conf_dumper() -> Type[ConfDumper]:
    if not ConfDumper.str_representer_added:
        ConfDumper.add_representer(str, ConfDumper.str_representer)
        ConfDumper.str_representer_added = True
    return ConfDumper


def config_to_yaml(cfg: Any, *, sort_keys: bool = False) -> str:
    """
    returns a yaml dump of this config object.

    :param cfg: Config object, Structured Config type or instance
    :param sort_keys: If True, will print dict keys in sorted order. default False.
    :return: A string containing the yaml representation.
    """
    res = yaml.dump(  # type: ignore
        cfg,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=sort_keys,
        Dumper=get_conf_dumper(),
    )

    return res
