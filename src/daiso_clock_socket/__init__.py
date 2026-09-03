import cadquery as cq
from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver
from pydantic import Field


class Param(BuildParam):
    clock_width: float = Field(76.0, description="時計の幅 (mm)")
    clock_depth: float = Field(18.5, description="時計の厚み (mm)")
    holder_height: float = Field(50.0, description="内側の保持高さ (mm)")
    clearance: float = Field(0.4, description="時計と内壁の片側クリアランス (mm)")
    wall: float = Field(2.0, description="側壁・背面・底の厚み (mm)")
    frame_thickness: float = Field(2.0, description="前面フレームの厚み (mm)")
    frame_lip: float = Field(3.0, description="前面フレームが時計に被さる幅 (mm)")
    fillet: float = Field(1.0, description="外周の縦エッジのフィレット半径 (mm)")
    hook: bool = Field(False, description="背面上部にフックを付ける (要サポート印刷)")
    hook_gap: float = Field(7.0, description="フックと背面の隙間 (mm)")
    hook_length: float = Field(30.0, description="フックの本体上端からの長さ (mm)")
    hook_thickness: float = Field(3.0, description="フックの厚み (mm)")
    hook_width: float | None = Field(
        None, description="フックの幅 (mm)。未指定なら本体の全幅 - 20mm"
    )
    hook_fillet: float = Field(
        1.0,
        description="フックの付け根・角のフィレット半径 (mm)。hook_thickness の半分未満にする",
    )

    @property
    def filename(self) -> str:
        hook = "-hook" if self.hook else ""
        return (
            f"v{ver()}-{self.clock_width}w{self.holder_height}h"
            f"{self.clock_depth}d{self.frame_lip}l{hook}.stl"
        )


def build(param: Param) -> cq.Workplane:
    # 使用時と同じ向き (底が Z=0、上面開放) で作る。この向きのまま印刷できる。
    # 前面 (-Y) はコの字フレーム (左右 + 下)、時計は上から差し込む。
    inner_w = param.clock_width + 2 * param.clearance
    inner_d = param.clock_depth + 2 * param.clearance
    outer_w = inner_w + 2 * param.wall
    outer_d = param.frame_thickness + inner_d + param.wall
    total_h = param.wall + param.holder_height

    window_w = param.clock_width - 2 * param.frame_lip
    cavity_y = -outer_d / 2 + param.frame_thickness + inner_d / 2
    front_y = -outer_d / 2 + param.frame_thickness / 2

    result = cq.Workplane("XY").box(
        outer_w, outer_d, total_h, centered=(True, True, False)
    )

    cavity = (
        cq.Workplane("XY", origin=(0, cavity_y, param.wall))
        .rect(inner_w, inner_d)
        .extrude(param.holder_height + 1)
    )

    window = (
        cq.Workplane("XY", origin=(0, front_y, param.wall + param.frame_lip))
        .rect(window_w, param.frame_thickness + 2)
        .extrude(param.holder_height + 1)
    )

    result = result.cut(cavity).cut(window)

    if param.fillet > 0:
        result = result.edges("|Z and (<X or >X)").fillet(param.fillet)

    if param.hook:
        # 背面上端から後方へ渡って垂れ下がる逆 L 字 (横から見て ┐ 形)
        hook_w = param.hook_width if param.hook_width is not None else outer_w - 20
        y0 = outer_d / 2
        t = param.hook_thickness
        hook = (
            cq.Workplane("YZ")
            .polyline(
                [
                    (y0, total_h),
                    (y0 + param.hook_gap + t, total_h),
                    (y0 + param.hook_gap + t, total_h - param.hook_length),
                    (y0 + param.hook_gap, total_h - param.hook_length),
                    (y0 + param.hook_gap, total_h - t),
                    (y0, total_h - t),
                ]
            )
            .close()
            .extrude(hook_w / 2, both=True)
        )
        if param.hook_fillet > 0:
            # 背面に接する 2 角 (<Y) 以外のプロファイル角を丸める
            hook = hook.edges("|X and (not <Y)").fillet(param.hook_fillet)
        result = result.union(hook)
        if param.hook_fillet > 0:
            # 付け根 (背面との接合部) の凹エッジを丸める
            root = cq.selectors.BoxSelector(
                (-hook_w / 2 - 1, y0 - 0.5, total_h - t - 0.5),
                (hook_w / 2 + 1, y0 + 0.5, total_h + 0.5),
            )
            result = result.edges(root).fillet(param.hook_fillet)

    return result


main = define_app(Param, build)
