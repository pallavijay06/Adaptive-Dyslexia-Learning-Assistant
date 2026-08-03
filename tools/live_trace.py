import json
import logging
import os
import functools
from datetime import datetime
from pathlib import Path

TRACE_DIR = Path("tools/trace_logs")
TRACE_DIR.mkdir(parents=True, exist_ok=True)

def _safe_json(obj):
    try:
        return json.dumps(obj, default=str, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return json.dumps(str(obj), ensure_ascii=False)
        except Exception:
            return repr(obj)

def _write_trace_file(name: str, content: str):
    filename = TRACE_DIR / f"live_trace_{datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')}_{name}.log"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return str(filename)

def _format_phase(phase_name: str, inp, outp):
    inp_type = type(inp).__name__
    out_type = type(outp).__name__
    try:
        inp_json = _safe_json(inp)
    except Exception:
        inp_json = repr(inp)
    try:
        out_json = _safe_json(outp)
    except Exception:
        out_json = repr(outp)

    def count(obj):
        if obj is None:
            return 0
        if isinstance(obj, (list, tuple, set, dict)):
            try:
                return len(obj)
            except Exception:
                return 1
        return 1

    parts = [
        "======================================================",
        f"{phase_name}",
        "======================================================",
        "\nInput:\n",
        f"Type: {inp_type}",
        f"Number of objects: {count(inp)}",
        "\n",
        inp_json,
        "\nOutput:\n",
        f"Type: {out_type}",
        f"Number of objects: {count(outp)}",
        "\n",
        out_json,
        "\n",
    ]
    return "\n".join(parts)

def attach_tracers():
    """Attach wrappers to target functions to log inputs/outputs to files.

    Returns a dict of wrapped function names -> log file paths for quick reference.
    """
    from backend import document_routes
    from services import visual_service
    from services import educational_understanding_engine
    from services import knowledge_organization_engine
    from services import educational_validation_engine
    from services import visualization_planning_engine
    from services import educational_visuals

    logs = {}

    def wrap_fn(module, fn_name, phase_name=None, special=None):
        orig = getattr(module, fn_name)

        @functools.wraps(orig)
        def wrapper(*args, **kwargs):
            try:
                inp = None
                # best-effort capture of first arg or request context
                if args:
                    inp = args[0]
                elif kwargs:
                    inp = kwargs
                # Call original
                out = orig(*args, **kwargs)
                # Special handling for Flask view functions: capture request JSON if present
                if phase_name is None:
                    ph = f"{module.__name__}.{fn_name}"
                else:
                    ph = phase_name

                # For _extract_visual_structure we want to print entering and full returned dict
                content = _format_phase(ph, inp, out)

                path = _write_trace_file(fn_name, content)
                logs[fn_name] = path
                logging.getLogger(__name__).info("Traced %s -> %s", ph, path)
                return out
            except Exception:
                # Ensure any exception preserves original behaviour
                raise

        setattr(module, fn_name, wrapper)
        return wrapper

    # Wrap document route visualize_document to capture the exact incoming request JSON
    try:
        import flask
        from flask import request

        orig_vis = document_routes.visualize_document

        @functools.wraps(orig_vis)
        def visualize_document_traced(document_id: int):
            # Log entering
            incoming = None
            try:
                incoming = flask.request.get_json(silent=True) or {}
            except Exception:
                incoming = None
            header = "Entering document_routes.visualize_document"
            parts = ["======================================================", header, "======================================================", "\nIncoming Request JSON:\n", _safe_json(incoming), "\n"]
            trace_path = _write_trace_file("visualize_request", "\n".join(parts))
            logging.getLogger(__name__).info("Saved incoming request to %s", trace_path)
            # Call original
            out = orig_vis(document_id)
            # Log the response body (Flask response object) as best-effort
            try:
                resp_json = None
                if hasattr(out, 'get_json'):
                    resp_json = out.get_json(silent=True)
                else:
                    resp_json = str(out)
            except Exception:
                resp_json = str(out)
            parts2 = ["======================================================", "document_routes.visualize_document Response", "======================================================", "\nResponse:\n", _safe_json(resp_json), "\n"]
            trace_path2 = _write_trace_file("visualize_response", "\n".join(parts2))
            logging.getLogger(__name__).info("Saved response to %s", trace_path2)
            return out

        document_routes.visualize_document = visualize_document_traced
        logs['visualize_document'] = trace_path
    except Exception:
        logging.getLogger(__name__).exception("Failed to wrap visualize_document")

    # Wrap high-level orchestration functions
    try:
        wrap_fn(visual_service, 'generate_visual_content', phase_name='PHASE: generate_visual_content')
        wrap_fn(visual_service, '_extract_visual_structure', phase_name='PHASE: _extract_visual_structure')
        # layout adaptor
        wrap_fn(visual_service, '_layout_model_to_renderer_nodes', phase_name='PHASE: _layout_model_to_renderer_nodes')
        wrap_fn(visual_service, '_generate_mindmap', phase_name='PHASE: _generate_mindmap')
    except Exception:
        logging.getLogger(__name__).exception("Failed to wrap visual_service functions")

    # Wrap engines
    try:
        wrap_fn(educational_understanding_engine, 'understand_chapter', phase_name='PHASE: Educational Understanding Engine')
        wrap_fn(knowledge_organization_engine, 'organize_knowledge', phase_name='PHASE: Knowledge Organization Engine')
        wrap_fn(educational_validation_engine, 'validate_educational_knowledge', phase_name='PHASE: Educational Validation Engine')
        # Wrap the VisualizationPlanningEngine.plan method
        orig_plan = visualization_planning_engine.VisualizationPlanningEngine.plan

        @functools.wraps(orig_plan)
        def plan_traced(self, structure):
            inp = getattr(structure, 'to_dict', lambda: structure)()
            out = orig_plan(self, structure)
            outd = getattr(out, 'to_dict', lambda: out)()
            content = _format_phase('PHASE: Visualization Planning Engine', inp, outd)
            path = _write_trace_file('visualization_planning_engine', content)
            logging.getLogger(__name__).info("Traced VisualizationPlanningEngine.plan -> %s", path)
            return out

        visualization_planning_engine.VisualizationPlanningEngine.plan = plan_traced
        logs['VisualizationPlanningEngine.plan'] = None
    except Exception:
        logging.getLogger(__name__).exception("Failed to wrap planning engine")

    # Wrap educational_visuals.create_mind_map to capture renderer input and post-render interpretation
    try:
        orig_create = educational_visuals.create_mind_map

        @functools.wraps(orig_create)
        def create_mind_map_traced(title: str, nodes: list[dict], theme: str = 'light'):
            # Save exact inputs
            pre = {
                'title': title,
                'nodes': nodes,
                'theme': theme,
            }
            pre_json = _safe_json(pre)
            pre_path = _write_trace_file('create_mind_map_input', pre_json)
            logging.getLogger(__name__).info("Saved create_mind_map input to %s", pre_path)

            out = orig_create(title, nodes, theme)

            # After render: interpret center, branches, children from input nodes
            center = title
            branches = [n.get('text') for n in (nodes or []) if isinstance(n, dict) and n.get('level', 1) == 1]
            children = [n.get('text') for n in (nodes or []) if isinstance(n, dict) and n.get('level', 1) == 2]

            post = {
                'center_node_text': center,
                'branch_labels': branches,
                'child_labels': children,
                'png_path': out,
            }
            post_json = _safe_json(post)
            post_path = _write_trace_file('create_mind_map_output', post_json)
            logging.getLogger(__name__).info("Saved create_mind_map output to %s", post_path)
            return out

        educational_visuals.create_mind_map = create_mind_map_traced
        logs['create_mind_map'] = None
    except Exception:
        logging.getLogger(__name__).exception("Failed to wrap create_mind_map")

    return logs
