// Persistence Of Vision raytracer version 2.0 sample file.

// non-Standard shapes #include file
// 

#declare Ellipsoid = quadric {
   <1.0, 1.0, 1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   -1.0
}

#declare light = light_source { <0, 0, 0> color White }

#declare USphere = intersection {
   sphere { <0, 0, 0>, 1 }
   plane { y, 0 inverse }
}


#declare DSphere = intersection {
   sphere { <0, 0, 0>, 1 }
   plane { -y, 0 inverse }
}

#declare Cylinder_X = quadric {
   <0.0, 1.0, 1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   -1.0
}

#declare Cylinder_Y = quadric {
   <1.0, 0.0, 1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   -1.0
}


#declare Cylinder_Z = quadric {
   <1.0, 1.0, 0.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   -1.0
}


#declare QCone_X = quadric {
   <-1.0, 1.0, 1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   0.0
}


#declare QCone_Y = quadric {
   <1.0, -1.0, 1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   0.0
}


#declare QCone_Z = quadric {
   <1.0, 1.0, -1.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   0.0
}

#declare DCone = /*---------CONE POINT DOWN /POINT at 000--------*/
intersection {
   object { QCone_Y scale <1, 1, 1> }
   plane { -y, 0 }
   plane { y, 1 }
}

#declare UCone = /*---------CONE POINT UP /POINT at 000--------*/
intersection {
   object { QCone_Y scale <1, 1, 1> }
   plane { y, 0 }
   plane { y, -1 inverse }
}

#declare BiCone = /*----2 CONES POINTS TOGETHER /POINT at 000---*/
intersection {
   object { QCone_Y scale <1, 1, 1> }
   plane { y, 1 }
   plane { y, -1 inverse }
}

#declare Plane_YZ = quadric {
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   <1.0, 0.0, 0.0>,
   0.0
}

#declare Plane_XZ = quadric {
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 1.0, 0.0>,
   0.0
}

#declare Plane_XY = quadric {
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 0.0>,
   <0.0, 0.0, 1.0>,
   0.0
}


/* y^2 + z^2 - x = 0 */
#declare Paraboloid_X = quadric {
   <0.0,  1.0,  1.0>,
   <0.0,  0.0,  0.0>,
   <-1.0, 0.0,  0.0>,
   0.0
}


/* x^2 + z^2 - y = 0 */
#declare Paraboloid_Y = quadric {
   <1.0,  0.0,  1.0>,
   <0.0,  0.0,  0.0>,
   <0.0, -1.0,  0.0>,
   0.0
}


/* x^2 + y^2 - z = 0 */
#declare Paraboloid_Z = quadric {
   <1.0,  1.0,  0.0>,
   <0.0,  0.0,  0.0>,
   <0.0,  0.0, -1.0>,
   0.0
}


/* y - x^2 + z^2 = 0 */
#declare Hyperboloid = quadric {
   < -1.0,  0.0,  1.0>,
   <  0.0,  0.0,  0.0>,
   <  0.0,  1.0,  0.0>,
   0.0
}


#declare Hyperboloid_Y = quadric {  /* Vertical hyperboloid */
   <1.0, -1.0,  1.0>,          /*                      */
   <0.0,  0.0,  0.0>,         /*            \   /     */
   <0.0,  0.0,  0.0>,        /* Like this:  ) (      */
   -1.0                     /*            /   \     */
}


#declare Cube = intersection {
   plane {  z, 1.0 }
   plane { -z, 1.0 }
   plane {  y, 1.0 }
   plane { -y, 1.0 }
   plane {  x, 1.0 }
   plane { -x, 1.0 }
}


#declare Tetrahedron = intersection {
   plane { -y, 1.0 }
   plane {  z, 1.0 rotate -30.0*x }
   plane {  x, 1.0 rotate <0.0, 30.0, 30.0> }
   plane { -x, 1.0 rotate <0.0, -30.0, -30.0> }
}


#declare Disk_X = intersection {       /* Capped cylinder, Length in x axis */
   object { Cylinder_X }
   plane { x, 0.0 inverse }
   plane { x, 1.0 }
}


#declare Disk_Y = intersection {       /* Capped cylinder, Length in y axis */
   object { Cylinder_Y }
   plane { y, 0.0 inverse }
   plane { y, 1.0 }
}


#declare Disk_Z = intersection {       /* Capped cylinder, Length in z axis */
   object { Cylinder_Z }
   plane { z, 0.0 inverse }
   plane { z, 1.0 }
}


#declare Hexagon = intersection {	        /* Hexagonal Solid, axis along x */
   plane { z, 1.0 }   /* Rotate 90 in z axis to stand up */
   plane { z, 1.0 rotate  60.0*x }
   plane { z, 1.0 rotate 120.0*x }
   plane { z, 1.0 rotate 180.0*x }
   plane { z, 1.0 rotate 240.0*x }
   plane { z, 1.0 rotate 300.0*x }
   plane { x, 1.0 }
   plane { x, -1.0 inverse }
}

#declare Rhomboid =			/* Three Dimensional 4-Sided Diamond */
intersection {
   plane { -x, 1.0 rotate -30.0*z }
   plane {  x, 1.0 rotate -30.0*z }
   plane {  z, 1.0 }
   plane { -z, 1.0 }
   plane {  y, 1.0 }
   plane { -y, 1.0 }
}
