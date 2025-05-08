import numpy as np

# Given values
M_vir_solar = 1.24e15  # in solar masses
r_vir_kpc = 3000       # in kpc
r_s_kpc = 333          # in kpc
# Constants
M_sun_g = 1.98847e33           # grams
kpc_to_cm = 3.086e21           # 1 kpc = 3.086e21 cm
solar_mass_to_gev = 5.62e23 * M_sun_g  # conversion: g -> GeV

# Convert inputs
M_vir_gev = M_vir_solar * solar_mass_to_gev
r_vir_cm = r_vir_kpc * kpc_to_cm

# Compute x = r_s / r_vir
x = r_s_kpc / r_vir_kpc

# Compute f(x)
f_x = x**3 * (np.log(1 + 1/x) - 1 / (1 + x))

# Compute rho_norm
rho_norm = M_vir_gev / (4 * np.pi * r_vir_cm**3 * f_x)


print(f"f(x) = {f_x:.6f}")
print(f"rho_norm = {rho_norm:.4e} GeV/cm^3")
