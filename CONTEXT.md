# QuADMESH

QuADMESH converts triangular meshes into quadrilateral meshes for 2D shallow-water models, following the layer-ordered QuADMESH+ algorithm. This file is the project glossary. Implementation choices live in `docs/adr/`.

## Language

**Layer**:
One band of elements counted inward from the domain boundary. Layer 0 touches the boundary.
_Avoid_: ring, shell, level

**Sweep**:
The pass that converts triangles to quads one layer at a time, from the innermost layer outward.
_Avoid_: march, scan

**Interior residual triangle**:
A triangle left after conversion that has no edge on the domain boundary. The algorithm must leave none.
_Avoid_: leftover tri, orphan triangle

**Boundary triangle**:
A triangle with at least one edge on the domain boundary. It may remain in intermediate or explicitly configured output.
_Avoid_: edge triangle

**Core stage**:
The conversion alone, `tri2quad`, with no post-processing or smoothing.
_Avoid_: matching stage, basic mode

**Full stage**:
The core stage followed by doublet collapse, vertex merging, boundary cleanup and smoothing.
_Avoid_: complete run

**Oracle**:
The Python package, treated as the reference that the C++ port is compared against.
_Avoid_: golden implementation, baseline code

**Ground truth**:
A saved oracle output for one input mesh and one stage, with its element counts and hash.
_Avoid_: expected file, snapshot

**Triangle marker**:
The convention that tells a mesh row it holds a triangle and not a quad. In the C++ port it is a trailing `-1`.
_Avoid_: padding trick, repeated vertex

## Relationships

- A **Sweep** visits every **Layer** once, innermost first.
- A **Ground truth** exists per mesh and per stage, so each mesh has one for the **Core stage** and one for the **Full stage**.
- The **Core stage** must leave zero **Interior residual triangles**. **Boundary triangles** may remain only in intermediate or configured output.

## Example dialogue

> **Dev:** The C++ run on Block_O left 40 triangles. Is that a failure?
> **Domain expert:** Count the **Interior residual triangles** first. If it is zero, the **Core stage** passed, and any **Boundary triangles** left are within the rules.
> **Dev:** And the element count differs from the **Ground truth** by two.
> **Domain expert:** Check which **Layer** diverged. A different tie in the **Sweep** can move the count, and that is allowed. An interior triangle never is.

## Flagged ambiguities

- "faithful" names port fidelity only. It is not a method name; the method is `quadmesh+`, with `layered` as its alias.
- "QuADMESH+" is the algorithm and API value. "QuADMESH" is the software, package and repository.
