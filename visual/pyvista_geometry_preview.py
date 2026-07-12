# -*- coding: utf-8 -*-
"""
几何预览渲染器。

负责模拟前几何类数据预览：
1. 角点网格预览；
2. 真实井轨迹预览；
3. 天然裂缝预览；
4. 人工裂缝几何预览。
"""

from __future__ import annotations

import numpy as np
import pyvista as pv

from .pyvista_static_property_preview import StaticPropertyPreviewRenderer


PREVIEW_ENABLE_ANTI_ALIASING = True
PREVIEW_ENABLE_DEPTH_PEELING = True
PREVIEW_DEPTH_PEEL_COUNT = 100
PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO = 0.0
PREVIEW_MAIN_LIGHT_INTENSITY = 1.6

GRID_SHOW_SURFACE = True
GRID_SHOW_EDGES = True
GRID_SURFACE_COLOR = (1.0, 1.0, 1.0)
GRID_SURFACE_OPACITY = 0.7
GRID_EDGE_COLOR = (0.5, 0.5, 0.5)

GRID_EDGE_LINE_WIDTH = 0.6
GRID_RENDER_LINES_AS_TUBES = True

GRID_POINT_MERGE_TOLERANCE_RATIO = 1e-9
GRID_POINT_MERGE_ABSOLUTE_TOLERANCE = 1e-8

GRID_LINE_OFFSET_FACTOR = -1.0
GRID_LINE_OFFSET_UNITS = -1.0
GRID_SURFACE_OFFSET_FACTOR = 1.0
GRID_SURFACE_OFFSET_UNITS = 1.0

WELL_COLOR = (0.08, 0.24, 0.62)
WELL_RADIUS = 2.0
WELL_OPACITY = 1.0
WELL_TUBE_SIDES = 32
WELL_FALLBACK_LINE_WIDTH = 4.0

NATURAL_FRACTURE_COLOR = (0.0, 0.25, 0.4)
NATURAL_FRACTURE_EDGE_COLOR = (0.0, 0.15, 0.25)
HYDRAULIC_FRACTURE_COLOR = (0.72, 0.38, 0.38)
HYDRAULIC_FRACTURE_EDGE_COLOR = (0.54, 0.29, 0.29)
FRACTURE_OPACITY = 1.0
FRACTURE_SHOW_EDGES = False
FRACTURE_EDGE_LINE_WIDTH = 0

FRACTURE_LIGHTING = False
FRACTURE_SMOOTH_SHADING = False
FRACTURE_AMBIENT = 1.0
FRACTURE_DIFFUSE = 0.0
FRACTURE_SPECULAR = 0.0

GEOMETRY_Z_TOL_RATIO = 0.02
GEOMETRY_Z_LOCAL_DEPTH_TOL_RATIO = 0.10
GEOMETRY_Z_ABS_TOL = 1e-6


class GeometryPreviewRenderer:
    def __init__(self, host):
        self.host = host
        self.plotter = host.plotter

        self._configure_preview_scene()

        self._grid_helper = StaticPropertyPreviewRenderer(host)

        self.grid_actor = None
        self.grid_edge_actor = None
        self.well_actors = []
        self.natural_fracture_actors = []
        self.hydraulic_fracture_actors = []


    def _configure_preview_scene(self):
        try:
            render_window = getattr(self.plotter, "ren_win", None)

            if render_window is not None:
                render_window.SetAlphaBitPlanes(1)
                render_window.SetMultiSamples(0)
        except Exception:
            pass

        try:
            renderer = getattr(self.plotter, "renderer", None)

            if renderer is not None:
                renderer.SetUseDepthPeeling(True)
                renderer.SetMaximumNumberOfPeels(PREVIEW_DEPTH_PEEL_COUNT)
                renderer.SetOcclusionRatio(PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO)
        except Exception:
            pass

        if PREVIEW_ENABLE_DEPTH_PEELING:
            try:
                self.plotter.enable_depth_peeling(
                    number_of_peels=PREVIEW_DEPTH_PEEL_COUNT,
                    occlusion_ratio=PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO,
                )
            except TypeError:
                try:
                    self.plotter.enable_depth_peeling()
                except Exception:
                    pass
            except Exception:
                pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                self.plotter.enable_anti_aliasing("fxaa")
            except TypeError:
                try:
                    self.plotter.enable_anti_aliasing()
                except Exception:
                    pass
            except Exception:
                pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                renderer = getattr(self.plotter, "renderer", None)

                if renderer is not None and hasattr(renderer, "SetUseFXAA"):
                    renderer.SetUseFXAA(True)
            except Exception:
                pass

        try:
            renderer = getattr(
                self.host,
                "renderer",
                None,
            )

            if renderer is None:
                renderer = getattr(
                    self.plotter,
                    "renderer",
                    None,
                )

            if renderer is not None:
                lights = renderer.GetLights()

                if lights is not None:
                    light = lights.GetItemAsObject(0)

                    if light:
                        light.SetIntensity(
                            PREVIEW_MAIN_LIGHT_INTENSITY
                        )

        except Exception:
            pass

    def _setup_camera_for_corner_grid_bounds(self, bounds):
        if bounds is None or len(bounds) != 6:
            return

        try:
            min_x, max_x, min_y, max_y, min_z, max_z = [
                float(value)
                for value in bounds
            ]

            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            cz = (min_z + max_z) / 2.0

            dx = max_x - min_x
            dy = max_y - min_y
            dz = max_z - min_z

            max_xy = max(dx, dy)
            z_ratio = dz / max_xy if max_xy > 0 else 1.0

            if z_ratio < 0.1:
                dist = max_xy * 1.8

                self.plotter.camera_position = [
                    (
                        cx + dx * 0.3,
                        cy - dist,
                        cz + dz * 8,
                    ),
                    (
                        cx,
                        cy,
                        cz,
                    ),
                    (
                        0,
                        0,
                        1,
                    ),
                ]

            else:
                dist = max(
                    dx,
                    dy,
                    dz,
                ) * 2.5

                self.plotter.camera_position = [
                    (
                        cx + dist * 0.8,
                        cy + dist * 0.6,
                        cz + dist * 0.4,
                    ),
                    (
                        cx,
                        cy,
                        cz,
                    ),
                    (
                        0,
                        0,
                        1,
                    ),
                ]

            self.plotter.reset_camera(
                render=False,
            )

            self.plotter.camera.Zoom(
                1.0,
            )

        except Exception:
            pass

    def clear_grid(self, render_now=True):
        self._remove_actor(self.grid_actor)
        self._remove_actor(self.grid_edge_actor)

        self.grid_actor = None
        self.grid_edge_actor = None

        if render_now:
            self._render()

    def clear_wells(self, render_now=True):
        self._remove_actor_list(self.well_actors)
        self.well_actors = []

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_natural_fractures(self, render_now=True):
        self._remove_actor_list(self.natural_fracture_actors)
        self.natural_fracture_actors = []

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_hydraulic_fractures(self, render_now=True):
        self._remove_actor_list(self.hydraulic_fracture_actors)
        self.hydraulic_fracture_actors = []

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_fractures(self, render_now=True):
        self.clear_natural_fractures(render_now=False)
        self.clear_hydraulic_fractures(render_now=False)

        if render_now:
            self._render()

    def clear_all(self, render_now=True):
        self.clear_grid(render_now=False)
        self.clear_wells(render_now=False)
        self.clear_fractures(render_now=False)

        setattr(
            self.host,
            "_preview_camera_session_key",
            None,
        )
        setattr(
            self.host,
            "_preview_camera_initialized",
            False,
        )

        if render_now:
            self._render()

    def is_grid_visible(self) -> bool:
        return self.grid_actor is not None or self.grid_edge_actor is not None

    def is_wells_visible(self) -> bool:
        return bool(self.well_actors)

    def is_natural_fractures_visible(self) -> bool:
        return bool(self.natural_fracture_actors)

    def is_hydraulic_fractures_visible(self) -> bool:
        return bool(self.hydraulic_fracture_actors)

    def is_fractures_visible(self) -> bool:
        return self.is_natural_fractures_visible() or self.is_hydraulic_fractures_visible()

    def _initialize_preview_camera_once(
        self,
        sim_data,
        bounds,
    ) -> bool:

        if bounds is None or len(bounds) != 6:
            return False

        session_key = id(sim_data)

        old_session_key = getattr(
            self.host,
            "_preview_camera_session_key",
            None,
        )

        if old_session_key != session_key:
            setattr(
                self.host,
                "_preview_camera_session_key",
                session_key,
            )
            setattr(
                self.host,
                "_preview_camera_initialized",
                False,
            )

        if bool(
            getattr(
                self.host,
                "_preview_camera_initialized",
                False,
            )
        ):
            return False

        self._setup_camera_for_corner_grid_bounds(
            bounds,
        )

        setattr(
            self.host,
            "_preview_camera_initialized",
            True,
        )

        return True

    @staticmethod
    def _actor_bounds(actor):
        if actor is None:
            return None

        try:
            bounds = actor.GetBounds()
        except Exception:
            try:
                bounds = actor.bounds
            except Exception:
                return None

        if bounds is None or len(bounds) != 6:
            return None

        values = np.asarray(
            bounds,
            dtype=np.float64,
        )

        if values.size != 6 or not np.isfinite(values).all():
            return None

        if (
            values[1] < values[0]
            or values[3] < values[2]
            or values[5] < values[4]
        ):
            return None

        return tuple(
            float(value)
            for value in values
        )

    def _actors_bounds(self, actors):
        valid_bounds = []

        for actor in actors or []:
            bounds = self._actor_bounds(actor)

            if bounds is not None:
                valid_bounds.append(bounds)

        if not valid_bounds:
            return None

        return (
            min(bounds[0] for bounds in valid_bounds),
            max(bounds[1] for bounds in valid_bounds),
            min(bounds[2] for bounds in valid_bounds),
            max(bounds[3] for bounds in valid_bounds),
            min(bounds[4] for bounds in valid_bounds),
            max(bounds[5] for bounds in valid_bounds),
        )

    def _main_renderer(self):
        renderer = getattr(
            self.plotter,
            "renderer",
            None,
        )

        if renderer is None:
            renderer = getattr(
                self.host,
                "renderer",
                None,
            )

        return renderer

    def _geometry_top_actors(self):
        return [
            actor
            for actor in [
                *(self.natural_fracture_actors or []),
                *(self.hydraulic_fracture_actors or []),
                *(self.well_actors or []),
            ]
            if actor is not None
        ]

    @staticmethod
    def _actor_is_visible(actor) -> bool:
        if actor is None:
            return False

        try:
            return bool(actor.GetVisibility())
        except Exception:
            try:
                return bool(actor.visibility)
            except Exception:
                return True

    def get_visible_geometry_bounds(self):
        actors = [
            actor
            for actor in self._geometry_top_actors()
            if self._actor_is_visible(actor)
        ]

        return self._actors_bounds(actors)

    @staticmethod
    def _renderer_is_attached(render_window, renderer) -> bool:
        if render_window is None or renderer is None:
            return False

        try:
            renderers = render_window.GetRenderers()

            if renderers is not None and hasattr(renderers, "IsItemPresent"):
                return bool(renderers.IsItemPresent(renderer))
        except Exception:
            pass

        return False

    def _set_geometry_overlay_attached(self, attached: bool) -> None:

        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )
        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if render_window is None or overlay_renderer is None:
            return

        is_attached = self._renderer_is_attached(
            render_window,
            overlay_renderer,
        )

        if attached and not is_attached:
            try:
                render_window.AddRenderer(overlay_renderer)
                is_attached = True
            except Exception:
                pass

        elif not attached and is_attached:
            try:
                render_window.RemoveRenderer(overlay_renderer)
                is_attached = False
            except Exception:
                pass

        setattr(
            self.host,
            "_geometry_preview_overlay_attached",
            bool(is_attached),
        )

        if not attached:
            main_renderer = self._main_renderer()

            if main_renderer is not None:
                try:
                    main_renderer.ResetCameraClippingRange()
                except Exception:
                    try:
                        self.plotter.reset_camera_clipping_range()
                    except Exception:
                        pass

    def _sync_geometry_overlay_attachment(self) -> None:

        has_geometry = bool(self._geometry_top_actors())

        if has_geometry:
            self._ensure_geometry_overlay_renderer(
                attach_to_window=True,
            )
        else:
            self._set_geometry_overlay_attached(False)

    def _ensure_geometry_overlay_renderer(
        self,
        attach_to_window: bool = True,
    ):

        main_renderer = self._main_renderer()
        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )

        if main_renderer is None or render_window is None:
            return None

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is None:
            try:
                overlay_renderer = main_renderer.NewInstance()
            except Exception:
                return None

            try:
                main_layer = int(main_renderer.GetLayer())
            except Exception:
                main_layer = 0

            try:
                current_layer_count = int(
                    render_window.GetNumberOfLayers()
                )
            except Exception:
                current_layer_count = 1

            overlay_layer = max(
                main_layer + 1,
                current_layer_count,
            )

            try:
                render_window.SetNumberOfLayers(
                    overlay_layer + 1
                )
                overlay_renderer.SetLayer(
                    overlay_layer
                )
            except Exception:
                return None

            setattr(
                self.host,
                "_geometry_preview_overlay_renderer",
                overlay_renderer,
            )
            setattr(
                self.host,
                "_geometry_preview_overlay_layer",
                overlay_layer,
            )
            setattr(
                self.host,
                "_geometry_preview_overlay_attached",
                False,
            )

        if attach_to_window:
            self._set_geometry_overlay_attached(True)

        try:
            overlay_renderer.SetActiveCamera(
                main_renderer.GetActiveCamera()
            )
        except Exception:
            pass

        try:
            overlay_renderer.SetViewport(
                *main_renderer.GetViewport()
            )
        except Exception:
            pass

        try:
            overlay_renderer.SetInteractive(False)
        except Exception:
            try:
                overlay_renderer.InteractiveOff()
            except Exception:
                pass

        try:
            overlay_renderer.SetPreserveColorBuffer(True)
        except Exception:
            try:
                overlay_renderer.PreserveColorBufferOn()
            except Exception:
                pass

        try:
            overlay_renderer.SetPreserveDepthBuffer(False)
        except Exception:
            try:
                overlay_renderer.PreserveDepthBufferOff()
            except Exception:
                pass

        try:
            overlay_renderer.SetBackgroundAlpha(0.0)
        except Exception:
            pass

        try:
            overlay_renderer.SetUseDepthPeeling(False)
        except Exception:
            pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                if hasattr(overlay_renderer, "SetUseFXAA"):
                    overlay_renderer.SetUseFXAA(True)
            except Exception:
                pass

        try:
            if hasattr(overlay_renderer, "AutomaticLightCreationOn"):
                overlay_renderer.AutomaticLightCreationOn()
        except Exception:
            pass

        return overlay_renderer

    @staticmethod
    def _configure_depth_sorted_geometry_actor(actor) -> None:

        if actor is None:
            return

        try:
            actor.ForceTranslucentOff()
        except Exception:
            try:
                actor.SetForceTranslucent(False)
            except Exception:
                pass

        try:
            actor.ForceOpaqueOn()
        except Exception:
            try:
                actor.SetForceOpaque(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.FrontfaceCullingOff()
                except Exception:
                    pass

                try:
                    prop.BackfaceCullingOff()
                except Exception:
                    pass

                try:
                    prop.RenderPointsAsSpheresOff()
                except Exception:
                    pass

        except Exception:
            pass

    def _move_actor_to_renderer_end(self, actor) -> None:
        if actor is None:
            return

        main_renderer = self._main_renderer()

        if main_renderer is None:
            return

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
            try:
                overlay_renderer.RemoveActor(actor)
            except Exception:
                pass

        try:
            main_renderer.RemoveActor(actor)
            main_renderer.AddActor(actor)
        except Exception:
            pass

    def _move_actor_to_geometry_overlay(self, actor) -> None:
        if actor is None:
            return

        overlay_renderer = self._ensure_geometry_overlay_renderer()

        if overlay_renderer is None:
            self._move_actor_to_renderer_end(actor)
            return

        main_renderer = self._main_renderer()

        if main_renderer is not None:
            try:
                main_renderer.RemoveActor(actor)
            except Exception:
                pass

        try:
            overlay_renderer.RemoveActor(actor)
        except Exception:
            pass

        try:
            overlay_renderer.AddActor(actor)
        except Exception:
            if main_renderer is not None:
                try:
                    main_renderer.AddActor(actor)
                except Exception:
                    pass

    def refresh_preview_stack(
        self,
        render_now=False,
    ) -> None:

        self._move_actor_to_renderer_end(
            self.grid_actor,
        )
        self._move_actor_to_renderer_end(
            self.grid_edge_actor,
        )

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_render_order",
        ):
            static_preview.refresh_render_order(
                render_now=False,
            )

        top_actors = self._geometry_top_actors()

        if top_actors:
            overlay_renderer = self._ensure_geometry_overlay_renderer(
                attach_to_window=True,
            )

            for actor in top_actors:
                self._configure_depth_sorted_geometry_actor(actor)
                self._move_actor_to_geometry_overlay(actor)

            if overlay_renderer is not None:
                main_renderer = self._main_renderer()

                if main_renderer is not None:
                    try:
                        overlay_renderer.SetActiveCamera(
                            main_renderer.GetActiveCamera()
                        )
                    except Exception:
                        pass
        else:
            self._set_geometry_overlay_attached(False)

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_layer_clipping_range",
        ):
            static_preview.refresh_layer_clipping_range(
                render_now=False,
            )

        if render_now:
            self._render()

    @staticmethod
    def _corner_grid_clean_tolerance(bounds):

        try:
            values = np.asarray(
                bounds,
                dtype=np.float64,
            ).reshape(6)

            spans = np.asarray(
                [
                    abs(values[1] - values[0]),
                    abs(values[3] - values[2]),
                    abs(values[5] - values[4]),
                ],
                dtype=np.float64,
            )

            finite_spans = spans[
                np.isfinite(spans)
            ]

            reference_span = (
                float(np.max(finite_spans))
                if finite_spans.size > 0
                else 0.0
            )

        except Exception:
            reference_span = 0.0

        return max(
            reference_span
            * GRID_POINT_MERGE_TOLERANCE_RATIO,
            GRID_POINT_MERGE_ABSOLUTE_TOLERANCE,
        )


    def _build_stable_corner_grid_surface_and_edges(
        self,
        grid,
    ):

        if grid is None:
            return None, None

        tolerance = self._corner_grid_clean_tolerance(
            grid.bounds,
        )

        stable_grid = grid

        try:
            stable_grid = grid.clean(
                tolerance=tolerance,
                remove_unused_points=True,
            )
        except TypeError:
            try:
                stable_grid = grid.clean(
                    tolerance=tolerance,
                )
            except Exception:
                stable_grid = grid
        except Exception:
            stable_grid = grid

        if (
            stable_grid is None
            or stable_grid.n_cells == 0
        ):
            stable_grid = grid

        surface = None
        edges = None

        try:
            surface = stable_grid.extract_surface()
        except Exception:
            surface = None

        if GRID_SHOW_EDGES:
            try:
                edges = stable_grid.extract_all_edges()
            except Exception:
                edges = None

        return surface, edges


    @staticmethod
    def _configure_stable_grid_edge_actor(actor):

        if actor is None:
            return

        try:
            actor.ForceTranslucentOff()
        except Exception:
            try:
                actor.SetForceTranslucent(False)
            except Exception:
                pass

        try:
            actor.ForceOpaqueOn()
        except Exception:
            try:
                actor.SetForceOpaque(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.SetOpacity(1.0)
                except Exception:
                    pass

                try:
                    prop.LightingOff()
                except Exception:
                    try:
                        prop.SetLighting(False)
                    except Exception:
                        pass

                try:
                    prop.SetLineWidth(
                        max(
                            float(GRID_EDGE_LINE_WIDTH),
                            1.0,
                        )
                    )
                except Exception:
                    pass

                if GRID_RENDER_LINES_AS_TUBES:
                    try:
                        prop.RenderLinesAsTubesOn()
                    except Exception:
                        try:
                            prop.SetRenderLinesAsTubes(True)
                        except Exception:
                            pass

        except Exception:
            pass

        try:
            mapper = actor.GetMapper()

            if mapper is not None:
                try:
                    mapper.ScalarVisibilityOff()
                except Exception:
                    try:
                        mapper.SetScalarVisibility(False)
                    except Exception:
                        pass

                try:
                    mapper.SetResolveCoincidentTopologyToPolygonOffset()
                except Exception:
                    pass

                try:
                    mapper.SetRelativeCoincidentTopologyLineOffsetParameters(
                        GRID_LINE_OFFSET_FACTOR,
                        GRID_LINE_OFFSET_UNITS,
                    )
                except Exception:
                    try:
                        mapper.SetResolveCoincidentTopologyLineOffsetParameters(
                            GRID_LINE_OFFSET_FACTOR,
                            GRID_LINE_OFFSET_UNITS,
                        )
                    except Exception:
                        pass

        except Exception:
            pass


    @staticmethod
    def _configure_stable_grid_surface_actor(actor):
        """
        关闭网格面光照，并将半透明面轻微压到线后方。
        """
        if actor is None:
            return

        try:
            actor.ForceOpaqueOff()
        except Exception:
            try:
                actor.SetForceOpaque(False)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.SetOpacity(
                        float(GRID_SURFACE_OPACITY)
                    )
                except Exception:
                    pass

                try:
                    prop.LightingOff()
                except Exception:
                    try:
                        prop.SetLighting(False)
                    except Exception:
                        pass

                try:
                    prop.EdgeVisibilityOff()
                except Exception:
                    try:
                        prop.SetEdgeVisibility(False)
                    except Exception:
                        pass

        except Exception:
            pass

        try:
            mapper = actor.GetMapper()

            if mapper is not None:
                try:
                    mapper.SetResolveCoincidentTopologyToPolygonOffset()
                except Exception:
                    pass

                try:
                    mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
                        GRID_SURFACE_OFFSET_FACTOR,
                        GRID_SURFACE_OFFSET_UNITS,
                    )
                except Exception:
                    try:
                        mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(
                            GRID_SURFACE_OFFSET_FACTOR,
                            GRID_SURFACE_OFFSET_UNITS,
                        )
                    except Exception:
                        pass

        except Exception:
            pass


    def render_grid(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()

        if self.is_grid_visible():
            self.clear_grid(render_now=render_now)
            return None

        self.clear_grid(render_now=False)

        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            if render_now:
                self._render()
            return None

        try:
            nx = int(grid_data["nx"])
            ny = int(grid_data["ny"])
            nz = int(grid_data["nz"])
        except Exception:
            if render_now:
                self._render()
            return None

        total = nx * ny * nz

        values = np.ones(
            total,
            dtype=np.float64,
        )

        actnum = np.asarray(
            grid_data.get(
                "actnum",
                np.ones(total, dtype=np.int32),
            ),
            dtype=np.int32,
        )

        if actnum.size != total:
            actnum = np.ones(
                total,
                dtype=np.int32,
            )

        mask = actnum == 1

        grid = self._grid_helper._build_corner_point_property_grid(
            grid_data=grid_data,
            values=values,
            mask=mask,
            scalar_name="GridPreview",
        )

        if grid is None or grid.n_cells == 0:
            if render_now:
                self._render()
            return None

        surface, edges = (
            self._build_stable_corner_grid_surface_and_edges(
                grid
            )
        )

        if (
            GRID_SHOW_EDGES
            and edges is not None
            and edges.n_points > 0
            and edges.n_cells > 0
        ):
            self.grid_edge_actor = self.plotter.add_mesh(
                edges,
                color=GRID_EDGE_COLOR,
                line_width=max(
                    float(GRID_EDGE_LINE_WIDTH),
                    1.0,
                ),
                opacity=1.0,
                lighting=False,
                render=False,
            )

            self._configure_stable_grid_edge_actor(
                self.grid_edge_actor
            )

        if (
            GRID_SHOW_SURFACE
            and surface is not None
            and surface.n_points > 0
            and surface.n_cells > 0
        ):
            self.grid_actor = self.plotter.add_mesh(
                surface,
                color=GRID_SURFACE_COLOR,
                opacity=GRID_SURFACE_OPACITY,
                show_edges=False,
                lighting=False,
                smooth_shading=False,
                render=False,
            )

            self._configure_stable_grid_surface_actor(
                self.grid_actor
            )

        self._initialize_preview_camera_once(
            sim_data=sim_data,
            bounds=grid.bounds,
        )

        self.refresh_preview_stack(
            render_now=False,
        )

        if render_now:
            self._render()

        return self.grid_actor or self.grid_edge_actor


    def render_wells(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()

        if self.is_wells_visible():
            self.clear_wells(render_now=render_now)
            return False

        self.clear_wells(render_now=False)

        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )

        if not isinstance(well_data, dict):
            if render_now:
                self._render()
            return False

        wells = well_data.get(
            "wells",
            [],
        )

        if not isinstance(wells, list) or not wells:
            if render_now:
                self._render()
            return False

        count = 0

        for well in wells:
            if not isinstance(well, dict):
                continue

            raw_track = well.get(
                "track",
                [],
            )

            if not isinstance(raw_track, list):
                continue

            valid_points = []

            for point in raw_track:
                if not isinstance(point, dict):
                    continue

                try:
                    md = float(point["md_m"])
                    x = float(point["x_m"])
                    y = float(point["y_m"])
                    z = float(point["z_m"])
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                if not np.isfinite([md, x, y, z]).all():
                    continue

                valid_points.append(
                    (
                        md,
                        np.array(
                            [x, y, z],
                            dtype=float,
                        ),
                    )
                )

            if len(valid_points) < 2:
                continue

            valid_points.sort(
                key=lambda item: item[0],
            )

            ordered_points = []

            for _, xyz in valid_points:
                if not ordered_points:
                    ordered_points.append(xyz)
                    continue

                if np.linalg.norm(xyz - ordered_points[-1]) > 1e-8:
                    ordered_points.append(xyz)

            if len(ordered_points) < 2:
                continue

            polyline = self._polyline_from_points(
                ordered_points,
            )

            if polyline is None:
                continue

            try:
                tube = polyline.tube(
                    radius=WELL_RADIUS,
                    n_sides=WELL_TUBE_SIDES,
                    capping=True,
                )

                actor = self.plotter.add_mesh(
                    tube,
                    color=WELL_COLOR,
                    opacity=WELL_OPACITY,
                    lighting=True,
                    smooth_shading=True,
                    ambient=0.75,
                    diffuse=0.90,
                    specular=0.20,
                    specular_power=20.0,
                    render=False,
                )

            except Exception:
                actor = self.plotter.add_mesh(
                    polyline,
                    color=WELL_COLOR,
                    line_width=WELL_FALLBACK_LINE_WIDTH,
                    opacity=WELL_OPACITY,
                    lighting=False,
                    render=False,
                )

            self._configure_depth_sorted_geometry_actor(actor)
            self.well_actors.append(actor)
            count += 1

        if count > 0:
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.well_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return count > 0

    def render_natural_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()

        if self.is_natural_fractures_visible():
            self.clear_natural_fractures(render_now=render_now)
            return False

        self.clear_natural_fractures(render_now=False)

        count = self._render_natural_fractures(
            sim_data,
        )

        if count > 0:
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.natural_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return count > 0

    def _render_natural_fractures(
        self,
        sim_data,
    ):
        dfn_data = getattr(
            sim_data,
            "static_dfn_data",
            None,
        )

        if not isinstance(dfn_data, dict):
            return 0

        fractures = dfn_data.get(
            "fractures",
            [],
        )

        if not isinstance(fractures, list) or not fractures:
            return 0

        grid_z_bounds = self._static_grid_z_bounds(sim_data)

        z_transform = self._build_geometry_z_transform(
            z_values=self._natural_fracture_z_values(fractures),
            grid_z_bounds=grid_z_bounds,
        )

        count = 0

        for fracture in fractures:
            if not isinstance(fracture, dict):
                continue

            vertices = fracture.get(
                "vertices",
                [],
            )

            points = self._safe_points(vertices)

            if points is None or len(points) < 3:
                continue

            points = self._apply_z_transform_to_points(
                points,
                z_transform,
            )

            if points is None or len(points) < 3:
                continue

            actors = self._add_fracture_polygon(
                points=points,
                color=NATURAL_FRACTURE_COLOR,
                edge_color=NATURAL_FRACTURE_EDGE_COLOR,
            )

            if actors:
                self.natural_fracture_actors.extend(actors)
                count += 1

        return count

    def render_hydraulic_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()

        if self.is_hydraulic_fractures_visible():
            self.clear_hydraulic_fractures(render_now=render_now)
            return False

        self.clear_hydraulic_fractures(render_now=False)

        count = self._render_hydraulic_fractures(
            sim_data,
        )

        if count > 0:
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.hydraulic_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return count > 0

    def _render_hydraulic_fractures(
        self,
        sim_data,
    ):
        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )

        if not isinstance(well_data, dict):
            return 0

        wells = well_data.get(
            "wells",
            [],
        )

        if not isinstance(wells, list):
            return 0

        grid_z_bounds = self._static_grid_z_bounds(sim_data)

        z_transform = self._build_geometry_z_transform(
            z_values=self._hydraulic_fracture_z_values(wells),
            grid_z_bounds=grid_z_bounds,
        )

        count = 0

        for well in wells:
            if not isinstance(well, dict):
                continue

            completions = well.get(
                "completion_definitions",
                [],
            )

            if not isinstance(completions, list):
                continue

            for completion in completions:
                if not isinstance(completion, dict):
                    continue

                if not completion.get("is_fractured", False):
                    continue

                fracture_data = completion.get(
                    "fracture",
                    None,
                )

                if not isinstance(fracture_data, dict):
                    continue

                if not fracture_data.get("geometry_available", False):
                    continue

                corners = fracture_data.get(
                    "corners",
                    [],
                )

                if not isinstance(corners, list) or len(corners) < 3:
                    continue

                raw_points = []

                for corner in corners:
                    if not isinstance(corner, dict):
                        continue

                    try:
                        raw_points.append(
                            (
                                float(corner["x_m"]),
                                float(corner["y_m"]),
                                float(corner["z_m"]),
                            )
                        )

                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        continue

                points = self._safe_points(raw_points)

                if points is None or len(points) < 3:
                    continue

                points = self._apply_z_transform_to_points(
                    points,
                    z_transform,
                )

                if points is None or len(points) < 3:
                    continue

                actors = self._add_fracture_polygon(
                    points=points,
                    color=HYDRAULIC_FRACTURE_COLOR,
                    edge_color=HYDRAULIC_FRACTURE_EDGE_COLOR,
                )

                if actors:
                    self.hydraulic_fracture_actors.extend(actors)
                    count += 1

        return count

    def render_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()

        if self.is_fractures_visible():
            self.clear_fractures(render_now=render_now)
            return False

        self.clear_fractures(render_now=False)

        total_count = 0

        total_count += self._render_natural_fractures(
            sim_data,
        )

        total_count += self._render_hydraulic_fractures(
            sim_data,
        )

        if total_count > 0:
            fracture_actors = [
                *(self.natural_fracture_actors or []),
                *(self.hydraulic_fracture_actors or []),
            ]

            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return total_count > 0

    def _static_grid_z_bounds(self, sim_data):
        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            return None

        z_values = []

        zcorn = grid_data.get(
            "zcorn",
            None,
        )

        if zcorn is not None:
            try:
                array = np.asarray(
                    zcorn,
                    dtype=np.float64,
                )

                finite = array[
                    np.isfinite(array)
                ]

                if finite.size > 0:
                    z_values.extend(
                        finite.tolist()
                    )

            except Exception:
                pass

        if not z_values:
            coord = grid_data.get(
                "coord",
                None,
            )

            if coord is not None:
                try:
                    coord_array = np.asarray(
                        coord,
                        dtype=np.float64,
                    ).reshape(
                        -1,
                        6,
                    )

                    z0 = coord_array[:, 2]
                    z1 = coord_array[:, 5]

                    z_array = np.concatenate(
                        [
                            z0,
                            z1,
                        ]
                    )

                    finite = z_array[
                        np.isfinite(z_array)
                    ]

                    if finite.size > 0:
                        z_values.extend(
                            finite.tolist()
                        )

                except Exception:
                    pass

        return self._finite_range(
            z_values,
        )

    @staticmethod
    def _natural_fracture_z_values(fractures):
        z_values = []

        if not isinstance(fractures, list):
            return z_values

        for fracture in fractures:
            if not isinstance(fracture, dict):
                continue

            vertices = fracture.get(
                "vertices",
                [],
            )

            points = GeometryPreviewRenderer._safe_points(
                vertices,
            )

            if points is None:
                continue

            z_values.extend(
                points[:, 2].tolist()
            )

        return z_values

    @staticmethod
    def _hydraulic_fracture_z_values(wells):
        z_values = []

        if not isinstance(wells, list):
            return z_values

        for well in wells:
            if not isinstance(well, dict):
                continue

            completions = well.get(
                "completion_definitions",
                [],
            )

            if not isinstance(completions, list):
                continue

            for completion in completions:
                if not isinstance(completion, dict):
                    continue

                if not completion.get("is_fractured", False):
                    continue

                fracture_data = completion.get(
                    "fracture",
                    None,
                )

                if not isinstance(fracture_data, dict):
                    continue

                if not fracture_data.get("geometry_available", False):
                    continue

                corners = fracture_data.get(
                    "corners",
                    [],
                )

                if not isinstance(corners, list):
                    continue

                for corner in corners:
                    if not isinstance(corner, dict):
                        continue

                    try:
                        z = float(
                            corner["z_m"]
                        )

                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        continue

                    if np.isfinite(z):
                        z_values.append(z)

        return z_values

    @staticmethod
    def _finite_range(values):
        try:
            array = np.asarray(
                values,
                dtype=np.float64,
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if array.size == 0:
            return None

        array = array[
            np.isfinite(array)
        ]

        if array.size == 0:
            return None

        return (
            float(np.min(array)),
            float(np.max(array)),
        )

    @staticmethod
    def _ranges_overlap(range_a, range_b, tolerance=0.0):
        if range_a is None or range_b is None:
            return False

        a_min, a_max = [
            float(value)
            for value in range_a
        ]

        b_min, b_max = [
            float(value)
            for value in range_b
        ]

        if a_max < a_min:
            a_min, a_max = a_max, a_min

        if b_max < b_min:
            b_min, b_max = b_max, b_min

        tolerance = max(
            float(tolerance),
            0.0,
        )

        return (
            a_min <= b_max + tolerance
            and b_min <= a_max + tolerance
        )

    def _build_geometry_z_transform(
        self,
        z_values,
        grid_z_bounds,
    ):
        input_range = self._finite_range(
            z_values,
        )

        if input_range is None:
            return lambda z: z

        if grid_z_bounds is None:
            return lambda z: z

        input_min, input_max = [
            float(value)
            for value in input_range
        ]

        grid_min, grid_max = [
            float(value)
            for value in grid_z_bounds
        ]

        if grid_max < grid_min:
            grid_min, grid_max = grid_max, grid_min

        if input_max < input_min:
            input_min, input_max = input_max, input_min

        grid_span = max(
            abs(grid_max - grid_min),
            GEOMETRY_Z_ABS_TOL,
        )

        input_span = max(
            abs(input_max - input_min),
            GEOMETRY_Z_ABS_TOL,
        )

        grid_tol = max(
            grid_span * GEOMETRY_Z_TOL_RATIO,
            GEOMETRY_Z_ABS_TOL,
        )

        local_depth_tol = max(
            grid_span * GEOMETRY_Z_LOCAL_DEPTH_TOL_RATIO,
            GEOMETRY_Z_ABS_TOL,
        )

        if self._ranges_overlap(
            (input_min, input_max),
            (grid_min, grid_max),
            grid_tol,
        ):
            return lambda z: z

        flipped_range = (
            -input_max,
            -input_min,
        )

        if self._ranges_overlap(
            flipped_range,
            (grid_min, grid_max),
            grid_tol,
        ):
            return lambda z: -z

        looks_like_local_depth = (
            input_min >= -local_depth_tol
            and input_span <= grid_span + local_depth_tol
        )

        shifted_range = (
            input_min + grid_min,
            input_max + grid_min,
        )

        if (
            looks_like_local_depth
            and self._ranges_overlap(
                shifted_range,
                (grid_min, grid_max),
                local_depth_tol,
            )
        ):
            return lambda z: z + grid_min

        return lambda z: z

    def _apply_z_transform_to_points(
        self,
        points,
        z_transform,
    ):
        points = self._safe_points(points)

        if points is None:
            return None

        transformed = points.copy()

        try:
            transformed[:, 2] = np.asarray(
                [
                    float(
                        z_transform(
                            float(z)
                        )
                    )
                    for z in transformed[:, 2]
                ],
                dtype=np.float64,
            )

        except Exception:
            return points

        mask = np.isfinite(
            transformed,
        ).all(
            axis=1,
        )

        transformed = transformed[
            mask
        ]

        if transformed.shape[0] == 0:
            return None

        return transformed

    @staticmethod
    def _polyline_from_points(points):
        if points is None or len(points) < 2:
            return None

        pts = np.asarray(
            points,
            dtype=np.float64,
        )

        if pts.ndim != 2 or pts.shape[1] != 3:
            return None

        if not np.isfinite(pts).all():
            return None

        lines = [len(pts)]

        for index in range(len(pts)):
            lines.append(index)

        polyline = pv.PolyData()
        polyline.points = pts
        polyline.lines = np.asarray(
            lines,
            dtype=np.int64,
        )

        return polyline

    @staticmethod
    def _safe_points(points):
        try:
            array = np.asarray(
                points,
                dtype=np.float64,
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if array.size == 0:
            return None

        try:
            array = array.reshape(
                -1,
                3,
            )

        except ValueError:
            return None

        mask = np.isfinite(array).all(axis=1)
        array = array[mask]

        if array.shape[0] == 0:
            return None

        return array

    def _add_fracture_polygon(
        self,
        points,
        color,
        edge_color,
    ):
        points = self._safe_points(points)

        if points is None or len(points) < 3:
            return []

        cleaned_points = []

        for point in points:
            if not cleaned_points:
                cleaned_points.append(point)
                continue

            if np.linalg.norm(point - cleaned_points[-1]) > 1e-8:
                cleaned_points.append(point)

        if (
            len(cleaned_points) >= 2
            and np.linalg.norm(cleaned_points[0] - cleaned_points[-1]) <= 1e-8
        ):
            cleaned_points.pop()

        if len(cleaned_points) < 3:
            return []

        points = np.asarray(
            cleaned_points,
            dtype=np.float64,
        )

        actors = []

        try:
            polygon = pv.PolyData()
            polygon.points = points
            polygon.faces = np.asarray(
                [len(points), *range(len(points))],
                dtype=np.int64,
            )

            actor = self.plotter.add_mesh(
                polygon,
                style="surface",
                color=color,
                opacity=FRACTURE_OPACITY,
                show_edges=False,
                edge_color=edge_color,
                line_width=0.0,
                lighting=FRACTURE_LIGHTING,
                smooth_shading=FRACTURE_SMOOTH_SHADING,
                ambient=FRACTURE_AMBIENT,
                diffuse=FRACTURE_DIFFUSE,
                specular=FRACTURE_SPECULAR,

                render=False,
            )

            self._configure_depth_sorted_geometry_actor(actor)
            actors.append(actor)

            if FRACTURE_EDGE_LINE_WIDTH > 0:
                edge_lines = []

                for index in range(len(points)):
                    start_point = points[index]
                    end_point = points[(index + 1) % len(points)]

                    edge_lines.append(
                        pv.Line(
                            start_point,
                            end_point,
                        )
                    )

                if edge_lines:
                    edge_actor = self.plotter.add_mesh(
                        pv.MultiBlock(edge_lines),
                        color=edge_color,
                        opacity=FRACTURE_OPACITY,
                        line_width=FRACTURE_EDGE_LINE_WIDTH,
                        lighting=False,
                        render=False,
                    )

                    self._configure_depth_sorted_geometry_actor(edge_actor)
                    actors.append(edge_actor)

            return actors

        except Exception:
            return []

    def _remove_actor(self, actor):
        if actor is None:
            return

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
            try:
                overlay_renderer.RemoveActor(actor)
            except Exception:
                pass

        main_renderer = self._main_renderer()

        if main_renderer is not None:
            try:
                main_renderer.RemoveActor(actor)
            except Exception:
                pass

        if hasattr(self.host, "_remove_actor"):
            try:
                self.host._remove_actor(actor)
                return
            except Exception:
                pass

        try:
            self.plotter.remove_actor(
                actor,
                render=False,
            )
        except Exception:
            pass

    def _remove_actor_list(self, actors):
        for actor in actors or []:
            self._remove_actor(actor)

    def _render(self):
        if hasattr(self.host, "_render"):
            self.host._render()
        else:
            self.plotter.render()

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_layer_clipping_range",
        ):
            layer_preview_active = (
                static_preview.refresh_layer_clipping_range(
                    render_now=False,
                )
            )

            if layer_preview_active:
                try:
                    self.plotter.render()
                except Exception:
                    pass