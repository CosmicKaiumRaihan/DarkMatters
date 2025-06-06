<<<<<<< Updated upstream
"""
DarkMatters.emissions module for calculating flux and surface brightness
"""
import numpy as np 
from scipy.integrate import simpson as integrate
from scipy.interpolate import interp1d,interpn,RegularGridInterpolator
from astropy import units,constants

def get_j_factor(theta_max,theta_min,dL,halo_func,mode_exp,rt):
    theta = np.logspace(np.log10(theta_min),np.log10(theta_max),num=51,axis=-1)
    zMax = dL*np.cos(theta) + np.sqrt(rt**2-dL**2*np.sin(theta)**2)
    zMin = dL*np.cos(theta) - np.sqrt(rt**2-dL**2*np.sin(theta)**2)
    zSet = np.logspace(np.log10(zMin),np.log10(zMax),num=51,axis=-1)
    rSet = np.sqrt(zSet**2+dL**2-2*zSet*dL*np.cos(np.tensordot(theta,np.ones(51),axes=0)))
    log10JFac = np.log10(integrate(y=integrate(y=halo_func(rSet)**mode_exp,x=zSet)*2*np.pi*np.sin(theta),x=theta))
    log10JFac = np.where(np.isnan(log10JFac),0.0,log10JFac)
    return log10JFac

def surface_brightness_loop(nu_sb,f_sample,r_sample,emm,delta_omega=4*np.pi,ergs=False):
    """
    Surface brightness from emmissivity 

    Arguments
    ---------------------------
    nu_sb : float
        Output frequency [MHz]
    f_sample : array-like float (m)
        All sampled frequencies [Mpc]
    r_sample : array-like float (n)
        Sampled radii for emissivity [Mpc]
    emm : array-like float (m,n)
        Emissivity [GeV cm^-3]
    delta_omega : float
        Angular area photons are distributed over [sr]
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    surface_brightness : array-like float (n)
        Surface brightness at frequency nu_sb [Jy arcminute^-2]
    """
    n = len(r_sample)
    sb = np.zeros(n,dtype=float) #surface brightness (nu,r)

    emm_int = RegularGridInterpolator((f_sample,r_sample),emm,fill_value=0.0,bounds_error=False)
    
    for j in range(0,n-1):
        rprime = r_sample[j]
        l_set = np.logspace(np.log10(r_sample[0]),np.log10(np.sqrt(r_sample[-1]**2-rprime**2)),num=101)
        r_set = np.sqrt(l_set**2+rprime**2)
        if len(f_sample) == 1:
            sb[j] = 2.0*integrate(y=emm_int((nu_sb*np.ones_like(r_set),r_set)),x=l_set)
        else:
            sb[j] = 2.0*integrate(y=emm_int((nu_sb*np.ones_like(r_set),r_set)),x=l_set)
    if not ergs:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV/cm^2")).to("Jy").value
    else:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV")).to("erg").value
        unit_factor *= nu_sb*(1*units.Unit("MHz")).to("Hz").value
    unit_factor *= 1.0/(1*units.Unit("sr")).to("arcmin^2").value #convert 1/sr to 1/arcminute^2
    return r_sample,sb/delta_omega*unit_factor#unit conversions applied


def flux_grid(rf,dl,f_sample,r_sample,emm,boost_mod=1.0,ergs=False):
    """
    Flux calculated from an emisssivity

    Arguments
    ---------------------------
    rf : float
        Radial integration limit [Mpc]
    dl : float
        Luminosity distance [Mpc] 
    f_sample : array-like float (n)
        Output frequency values [MHz]
    r_sample : array-like float (m)
        Sampled radii for emissivity [Mpc]
    emm : array-like float (n,m) 
        Emissivity [GeV cm^-3]
    boost_mod : float
        Flux boosting factor
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    flux : array-like float (n)
        Output fluxes [Jy]
    """
    if len(r_sample) < 101:
        newr_sample = np.logspace(np.log10(r_sample[0]),np.log10(rf),num=101)
    else:
        newr_sample = r_sample
    if len(f_sample) == 1:
        em_int = interp1d(r_sample,emm[0],bounds_error=False,fill_value=0.0)
        r_grid = newr_sample
        flux_grid = r_grid**2*em_int(newr_sample)/(dl**2 + r_grid**2)
    else:
        f_grid,r_grid = np.meshgrid(f_sample,newr_sample,indexing="ij")
        em_int = interpn((f_sample,r_sample),emm,(f_grid,r_grid),bounds_error=False,fill_value=0.0)#interp2d(r_sample,f_sample,emm)
        flux_grid = r_grid**2*em_int/(dl**2 + r_grid**2)
    if not ergs:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV/cm^2")).to("Jy").value
    else:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV")).to("erg").value
        unit_factor *= f_sample*(1*units.Unit("MHz")).to("Hz").value
    return integrate(y=flux_grid,x=r_grid)*unit_factor*boost_mod

def flux_from_j_factor(mx,z,j_factor,f_sample,g_sample,q_sample,mode_exp,ergs=False):
    """
    Prompt gamma-ray flux determined via J-factor

    Arguments
    ---------------------------
    mx : float
        WIMP mass [GeV]
    z : float
        Halo redshift
    j_factor : float
        The "J-factor" of the halo [GeV^2/cm^5]
    f_sample : array-like float
        Output frequency values [MHz]
    g_sample : array-like float
        Yield spectrum Lorentz-gamma values
    q_sample : array-like float
        (Yield spectrum * electron mass) [particles per annihilation]
    mode_exp : float
        2 for annihilation, 1 for decay
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    flux : array-like float
        Output flux from annihilation
    """
    num = len(f_sample)
    h = constants.h.to('GeV s').value
    me = (constants.m_e*constants.c**2).to('GeV').value #electron mass (GeV)
    nwimp0 = 0.25/np.pi/mx**mode_exp/mode_exp #GeV^-2
    emm = np.zeros(num,dtype=float)
    Q_func = interp1d(g_sample,q_sample)
    for i in range(0,num):
        E_g = h*f_sample[i]*1e6*(1+z)/me
        if E_g < g_sample[0] or E_g > g_sample[-1]:
            emm[i] = 0.0
        else:
            emm[i] = Q_func(E_g)*j_factor*nwimp0*E_g #units of cm^-2 s^-1
    if not ergs:
        unit_factor = constants.h.to("J/Hz").value/1e-26*1e4 #Jy (cm^-2 -> m^-2 (1e4), Jy = 1e-26 W/m^2/Hz)
    else:
        unit_factor = constants.h.to('erg/MHz').value*f_sample #erg cm^-2 s^-1
=======
"""
DarkMatters.emissions module for calculating flux and surface brightness
"""
import numpy as np 
from scipy.integrate import simpson as integrate
from scipy.interpolate import interp1d,interpn,RegularGridInterpolator
from astropy import units,constants

def get_j_factor(theta_max,theta_min,dL,halo_func,mode_exp,rt):
    theta = np.logspace(np.log10(theta_min),np.log10(theta_max),num=51,axis=-1)
    zMax = dL*np.cos(theta) + np.sqrt(rt**2-dL**2*np.sin(theta)**2)
    zMin = dL*np.cos(theta) - np.sqrt(rt**2-dL**2*np.sin(theta)**2)
    zSet = np.logspace(np.log10(zMin),np.log10(zMax),num=51,axis=-1)
    rSet = np.sqrt(zSet**2+dL**2-2*zSet*dL*np.cos(np.tensordot(theta,np.ones(51),axes=0)))
    log10JFac = np.log10(integrate(y=integrate(y=halo_func(rSet)**mode_exp,x=zSet)*2*np.pi*np.sin(theta),x=theta))
    log10JFac = np.where(np.isnan(log10JFac),0.0,log10JFac)
    return log10JFac

def surface_brightness_loop(nu_sb,f_sample,r_sample,emm,delta_omega=4*np.pi,ergs=False):
    """
    Surface brightness from emmissivity 

    Arguments
    ---------------------------
    nu_sb : float
        Output frequency [MHz]
    f_sample : array-like float (m)
        All sampled frequencies [Mpc]
    r_sample : array-like float (n)
        Sampled radii for emissivity [Mpc]
    emm : array-like float (m,n)
        Emissivity [GeV cm^-3]
    delta_omega : float
        Angular area photons are distributed over [sr]
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    surface_brightness : array-like float (n)
        Surface brightness at frequency nu_sb [Jy arcminute^-2]
    """
    n = len(r_sample)
    sb = np.zeros(n,dtype=float) #surface brightness (nu,r)

    emm_int = RegularGridInterpolator((f_sample,r_sample),emm,fill_value=0.0,bounds_error=False)
    
    for j in range(0,n-1):
        rprime = r_sample[j]
        l_set = np.logspace(np.log10(r_sample[0]),np.log10(np.sqrt(r_sample[-1]**2-rprime**2)),num=101)
        r_set = np.sqrt(l_set**2+rprime**2)
        if len(f_sample) == 1:
            sb[j] = 2.0*integrate(y=emm_int((nu_sb*np.ones_like(r_set),r_set)),x=l_set)
        else:
            sb[j] = 2.0*integrate(y=emm_int((nu_sb*np.ones_like(r_set),r_set)),x=l_set)
    delta_omega *= (1*units.Unit("sr")) #convert sr to arcminute^2
    if not ergs:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV/cm^2")).to("Jy").value
    else:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV")).to("erg").value
        unit_factor *= nu_sb*(1*units.Unit("MHz")).to("Hz").value
    return r_sample,sb*unit_factor/delta_omega #unit conversions and adjustment to angles 


def flux_grid(rf,dl,f_sample,r_sample,emm,boost_mod=1.0,ergs=False):
    """
    Flux calculated from an emisssivity

    Arguments
    ---------------------------
    rf : float
        Radial integration limit [Mpc]
    dl : float
        Luminosity distance [Mpc] 
    f_sample : array-like float (n)
        Output frequency values [MHz]
    r_sample : array-like float (m)
        Sampled radii for emissivity [Mpc]
    emm : array-like float (n,m) 
        Emissivity [GeV cm^-3]
    boost_mod : float
        Flux boosting factor
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    flux : array-like float (n)
        Output fluxes [Jy]
    """
    if len(r_sample) < 101:
        newr_sample = np.logspace(np.log10(r_sample[0]),np.log10(rf),num=101)
    else:
        newr_sample = r_sample
    if len(f_sample) == 1:
        em_int = interp1d(r_sample,emm[0],bounds_error=False,fill_value=0.0)
        r_grid = newr_sample
        flux_grid = r_grid**2*em_int(newr_sample)/(dl**2 + r_grid**2)
    else:
        f_grid,r_grid = np.meshgrid(f_sample,newr_sample,indexing="ij")
        em_int = interpn((f_sample,r_sample),emm,(f_grid,r_grid),bounds_error=False,fill_value=0.0)#interp2d(r_sample,f_sample,emm)
        flux_grid = r_grid**2*em_int/(dl**2 + r_grid**2)
    if not ergs:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV/cm^2")).to("Jy").value
    else:
        unit_factor = (1*units.Unit("Mpc")).to("cm").value
        unit_factor *= (1*units.Unit("GeV")).to("erg").value
        unit_factor *= f_sample*(1*units.Unit("MHz")).to("Hz").value
    return integrate(y=flux_grid,x=r_grid)*unit_factor*boost_mod

def flux_from_j_factor(mx,z,j_factor,f_sample,g_sample,q_sample,mode_exp,ergs=False):
    """
    Prompt gamma-ray flux determined via J-factor

    Arguments
    ---------------------------
    mx : float
        WIMP mass [GeV]
    z : float
        Halo redshift
    j_factor : float
        The "J-factor" of the halo [GeV^2/cm^5]
    f_sample : array-like float
        Output frequency values [MHz]
    g_sample : array-like float
        Yield spectrum Lorentz-gamma values
    q_sample : array-like float
        (Yield spectrum * electron mass) [particles per annihilation]
    mode_exp : float
        2 for annihilation, 1 for decay
    ergs : boolean, optional
        If True use CGS units in output 

    Returns
    ---------------------------
    flux : array-like float
        Output flux from annihilation
    """
    num = len(f_sample)
    h = constants.h.to('GeV s').value
    me = (constants.m_e*constants.c**2).to('GeV').value #electron mass (GeV)
    nwimp0 = 0.25/np.pi/mx**mode_exp/mode_exp #GeV^-2
    emm = np.zeros(num,dtype=float)
    Q_func = interp1d(g_sample,q_sample)
    for i in range(0,num):
        E_g = h*f_sample[i]*1e6*(1+z)/me
        if E_g < g_sample[0] or E_g > g_sample[-1]:
            emm[i] = 0.0
        else:
            emm[i] = Q_func(E_g)*j_factor*nwimp0*E_g #units of cm^-2 s^-1
    if not ergs:
        unit_factor = constants.h.to("J/Hz").value/1e-26*1e4 #Jy (cm^-2 -> m^-2 (1e4), Jy = 1e-26 W/m^2/Hz)
    else:
        unit_factor = constants.h.to('erg/MHz').value*f_sample #erg cm^-2 s^-1
>>>>>>> Stashed changes
    return 2.0*emm*unit_factor #2 gamma-rays per event