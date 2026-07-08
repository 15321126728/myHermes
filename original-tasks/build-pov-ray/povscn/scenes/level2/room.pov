// Persistence Of Vision raytracer version 2.0 sample file.

// By Drew Wells

// Room.pov - Empty room created for cis Comart Raytracing Group Project

#include "shapes.inc"
#include "colors.inc"
#include "textures.inc"

/* Camera Facing North*/
camera {
   direction <0.0, 0.0, 1.5>
   up  <0.0, 1.0, 0.0>
   right <4/3, 0.0, 0.0>
   translate < 10.0, 5.0, -30.0>
   look_at <0.0, 5.0, 0.0>
}

/*************************************************/
/* Define objects for use in scene               */
/* Your object should be DECLAREd here           */
/*************************************************/

#declare North_Wall =
plane { z, 10.0
   pigment { 
      granite
      scale <1.0, 20.0, 1.0>
      quick_color Yellow
   }
}
/* South Wall commented out so camera can see in*/
#declare South_Wall =
plane { z, -10.0
   pigment { 
      Cherry_Wood
      scale 10.0
      quick_color Red
   }
   finish { crand 0.05 }
}

/* Not visible with current viewpoint*/
/* But could be useful for light coming through window etc. */

#declare East_Wall =
plane { x, 15.0
   pigment  {
      Jade
      scale 10.0
      quick_color Green
   }
}

#declare West_Wall =
plane { x, -15.0
   pigment { 
      White_Wood
      scale <15.0, 20.0, 3.0>
      quick_color White
   }
   finish { crand 0.05 }
}

#declare Ceiling =
plane { y, 15.0
   pigment { 
      Red_Marble
      scale 10.0
      quick_color Red
   }
} 
#declare Floor =
plane { y, 0.0
   pigment { 
      Pine_Wood
      scale <40.0, 3.0, 3.0>
      quick_color Violet
   }
   finish { crand 0.05 }
}

/*******************************************/
/* Scene description                       */
/*******************************************/
object {
   North_Wall
}

/* Comment out South Wall so camera can see in */
/*object {
  South_Wall
}*/

object {
   East_Wall
}

object {
   West_Wall
}

object {
   Ceiling
}

object {
   Floor
}

/* Colored spheres to help visualize coordinates*/
sphere {
   <0.0, 7.0, 9.0> 1.0
   pigment { Yellow }
}

/* South sphere not visible in example gif*/
/*object {South}
sphere { <0.0, 5.0, -10.0>, 1.0
    pigment { Red }
}*/

sphere { /*East*/
   <10.0, 7.0, 0.0>, 1.0
   pigment { color Green }
}

sphere { /*West*/
   <-14.0, 7.0, 0.0>, 1.0
   pigment { Blue }
}

sphere { /*Up*/
   <0.0, 14.0, 0.0>, 1.0
   pigment { White }
}

sphere { /*Down*/
   <0.0, 1.0, 0.0>, 1.0
   pigment { color Violet }
}

/*Crude Spot light - feel free to add more light sources.*/
union {
   intersection {
      sphere { <0.0, 0.0, 0.0>, 2.0 inverse }
      sphere { <0.0, 0.0, 0.0>, 2.1 }
      plane {  <0.0, 0.0, 1.0>, 1.2 }

      pigment {
         Brown_Agate
         scale 3.0
      }
      finish { specular 1.0 }
      rotate <45.0, -40.0, 0.0>
      translate <10.0, 10.0, -8.0>
   }

   light_source { <10.0, 10.0, -8.0> colour White }
}

/* Far light source to light where spot doesn't */   
light_source { <-10.0, 10.0, -40.0> colour White }
