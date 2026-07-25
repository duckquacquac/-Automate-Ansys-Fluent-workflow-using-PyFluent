# Automate Ansys Fluent Workflow Using PyFluent

*Disclaimer: This post is written to the best of my knowledge – 4th year MechE student.*

During my time working on Airbrakes for a high-powered rocket competition (IREC), an ambitious goal was to characterize the behavior of airbrakes under different flight regimes, especially drag force and drag coefficient. A quick analysis leads to:

$$C_d = f(\text{geometry}, Re, Ma)$$

The next best way to measure those values, short of experimental testing, is CFD. However, manually sweeping across all parameters is costly and time-consuming. The approach I chose for IREC was to take the flight trajectory, extract the realistic (Re, Ma) pairs at different points along the trajectory, and characterize drag around those points only. That approach significantly lowers the number of data points required, but it could become very inaccurate once the vehicle deviates from its trajectory.

With the help of Claude and PyFluent, I extended the possible sweep range by automating the Fluent workflow. Here is my workflow:

1. Create the enclosure volume using SolidWorks (the tool I'm most familiar with)
2. Create named selections using SpaceClaim. I have not figured out a way to do named selections with code, and I highly doubt it's doable.
3. Mesh one case using PyFluent, no GUI. Examine the mesh afterward using the GUI.
4. Run one case using PyFluent, no GUI. Examine the case afterward using the GUI.
5. Extract the variables of interest and verify y+/y*.
6. Modify meshing/solving conditions to achieve the y+/y* goal. Mesh all geometries using PyFluent.
7. Create a sweep table containing geometry and boundary conditions. Set a reasonable residual range so Fluent does not have to run through all iterations.
8. Run the solver code through a loop, iterating through the sweep table to run all cases. Extract data to a .csv file. I believe visualization is possible too.

I was able to run ~200 Fluent cases in ~4-5 nights, all automated, and am still working on the data processing step. This significantly improved my ability to characterize fluid behavior using Fluent. I uploaded the whole working directory on GitHub if any of you are interested in replicating the work.

I would welcome any discussion or advice for future CFD work!
