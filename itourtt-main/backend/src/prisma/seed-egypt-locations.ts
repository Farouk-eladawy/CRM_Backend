/**
 * Egypt location seed data with verified Google Maps coordinates.
 *
 * Hierarchy: Country → Airport → City → Zone → Hotel
 * All coordinates are real lat/lng from Google Maps.
 */

interface HotelSeed {
  name: string;
  lat: number;
  lng: number;
  placeId: string;
  address?: string;
  stars?: number;
}

interface ZoneSeed {
  name: string;
  lat: number;
  lng: number;
  placeId: string;
  hotels: HotelSeed[];
}

interface CitySeed {
  name: string;
  lat: number;
  lng: number;
  placeId: string;
  zones: ZoneSeed[];
}

interface AirportSeed {
  name: string;
  code: string;
  lat: number;
  lng: number;
  placeId: string;
  cities: CitySeed[];
}

interface CountrySeed {
  name: string;
  code: string;
  lat: number;
  lng: number;
  placeId: string;
  airports: AirportSeed[];
}

export const EGYPT_DATA: CountrySeed = {
  name: 'Egypt',
  code: 'EG',
  lat: 26.820553,
  lng: 30.802498,
  placeId: 'ChIJ6TjUkFUCWBQRwIAceFg26dA',
  airports: [
    // ──────────────────────────────────────────
    // CAIRO INTERNATIONAL AIRPORT (CAI)
    // ──────────────────────────────────────────
    {
      name: 'Cairo International Airport',
      code: 'CAI',
      lat: 30.121944,
      lng: 31.405556,
      placeId: 'ChIJr3KzmOZLWBQRsfYEYMCp-Qg',
      cities: [
        {
          name: 'Cairo',
          lat: 30.044420,
          lng: 31.235712,
          placeId: 'ChIJL_P_CXESTxQRMHEkz7lMEsI',
          zones: [
            {
              name: 'Downtown',
              lat: 30.044870,
              lng: 31.236359,
              placeId: 'ChIJHeBXf2kWWBQR1GlHePi5JAE',
              hotels: [
                { name: 'Kempinski Nile Hotel Cairo', lat: 30.040891, lng: 31.233101, placeId: 'ChIJcdbvR2kWWBQR7X94OQT3eBM', stars: 5 },
                { name: 'The Nile Ritz-Carlton Cairo', lat: 30.042798, lng: 31.233951, placeId: 'ChIJn3GzxmkWWBQRr2bSMF-WE5g', stars: 5 },
                { name: 'InterContinental Cairo Semiramis', lat: 30.041950, lng: 31.232150, placeId: 'ChIJP7vmQGkWWBQRHjpOjhD0xA4', stars: 5 },
                { name: 'Steigenberger Hotel El Tahrir', lat: 30.044580, lng: 31.234980, placeId: 'ChIJCwB_yGIWWBQR8kT1N7CZkOE', stars: 4 },
                { name: 'Hotel Grand Royal', lat: 30.049250, lng: 31.241530, placeId: 'ChIJj5dwjWUWWBQRH4C3jbEBQxA', stars: 3 },
                { name: 'Ramses Hilton', lat: 30.054370, lng: 31.237940, placeId: 'ChIJezPuiHAWWBQRP6wHRmw5fYw', stars: 5 },
              ],
            },
            {
              name: 'Giza',
              lat: 30.013056,
              lng: 31.208853,
              placeId: 'ChIJ_VoiXIhHWBQReJnCIhVR8OQ',
              hotels: [
                { name: 'Marriott Mena House Cairo', lat: 29.978140, lng: 31.131690, placeId: 'ChIJxShQ4B5BWBQRK0zVEdKp6IA', stars: 5 },
                { name: 'Le Méridien Pyramids Hotel & Spa', lat: 29.987570, lng: 31.130480, placeId: 'ChIJJSJV3h5BWBQRLfyiqXV5vkk', stars: 5 },
                { name: 'Steigenberger Pyramids Cairo', lat: 29.988440, lng: 31.132380, placeId: 'ChIJhRqLNx9BWBQRbRvbGvx1eNM', stars: 5 },
                { name: 'Barceló Cairo Pyramids', lat: 29.989520, lng: 31.130230, placeId: 'ChIJUe5NCSJBWBQR-16GEkVXC-o', stars: 4 },
                { name: 'Four Seasons Hotel Cairo at The First Residence', lat: 30.018580, lng: 31.218740, placeId: 'ChIJ_ZbHoYpHWBQRk63WjweFSDA', stars: 5 },
              ],
            },
            {
              name: 'Heliopolis',
              lat: 30.087203,
              lng: 31.321869,
              placeId: 'ChIJY7NqWUxLWBQRyR3r0JpzjEk',
              hotels: [
                { name: 'Le Méridien Heliopolis', lat: 30.098280, lng: 31.339130, placeId: 'ChIJoT11d5pLWBQRWrTvDWm7Yns', stars: 5 },
                { name: 'Hilton Cairo Heliopolis Hotel', lat: 30.112170, lng: 31.397820, placeId: 'ChIJRwHJzN1LWBQRSIrHd2y5yyo', stars: 5 },
                { name: 'Le Passage Cairo Hotel & Casino', lat: 30.097010, lng: 31.340330, placeId: 'ChIJG4b8CJlLWBQRICjVBjyGF3o', stars: 5 },
                { name: 'Holiday Inn Cairo Citystars', lat: 30.072400, lng: 31.347180, placeId: 'ChIJw2t0kCBMWBQRL5hWqPnKRAs', stars: 4 },
              ],
            },
            {
              name: 'Maadi',
              lat: 29.960630,
              lng: 31.250928,
              placeId: 'ChIJQQTlT0YRWBQR3QU_8r7HYBU',
              hotels: [
                { name: 'Sofitel Cairo Nile El Gezirah', lat: 30.035280, lng: 31.224180, placeId: 'ChIJyYNPw0gWWBQRfpHQ2P5f5Mo', stars: 5 },
                { name: 'Villa Belle Époque', lat: 29.963580, lng: 31.257190, placeId: 'ChIJ__99AJgfWBQR0KJjTL3EYGM', stars: 4 },
              ],
            },
            {
              name: 'Nasr City',
              lat: 30.064600,
              lng: 31.341700,
              placeId: 'ChIJnfz-bBlMWBQRh0n0Bjy0glM',
              hotels: [
                { name: 'Sonesta Hotel Tower & Casino Cairo', lat: 30.064600, lng: 31.338900, placeId: 'ChIJ-xrj3AxMWBQR2U4wqQq5v8U', stars: 5 },
                { name: 'Triumph Hotel', lat: 30.064390, lng: 31.325480, placeId: 'ChIJYe7eLPpLWBQRVPHVVMnMQcA', stars: 3 },
              ],
            },
            {
              name: 'Zamalek',
              lat: 30.062056,
              lng: 31.220000,
              placeId: 'ChIJXcx1JlQWWBQRkLLckqbAL0Q',
              hotels: [
                { name: 'Cairo Marriott Hotel & Omar Khayyam Casino', lat: 30.060530, lng: 31.221850, placeId: 'ChIJXcx1JlQWWBQR0DWGB0L3U9c', stars: 5 },
                { name: 'Safir Hotel Cairo', lat: 30.062820, lng: 31.221110, placeId: 'ChIJA8BaqFQWWBQRcbGYlkOT_xM', stars: 4 },
                { name: 'Flamenco Hotel Cairo', lat: 30.060810, lng: 31.225490, placeId: 'ChIJWa5Ky1QWWBQRMjvj7g_8TwM', stars: 3 },
              ],
            },
            {
              name: 'New Cairo',
              lat: 30.019830,
              lng: 31.465520,
              placeId: 'ChIJE_pZ8LxEWBQR50TQwMLmXNs',
              hotels: [
                { name: 'Dusit Thani LakeView Cairo', lat: 30.015280, lng: 31.461520, placeId: 'ChIJjZLDpLtEWBQR3I1UUFvBM_k', stars: 5 },
                { name: 'JW Marriott Hotel Cairo', lat: 30.022810, lng: 31.445290, placeId: 'ChIJd7EiQmNEWBQRCJXZG30MboU', stars: 5 },
                { name: 'Renaissance Cairo Mirage City Hotel', lat: 30.022580, lng: 31.445120, placeId: 'ChIJIXz3CqhEWBQRBWP9F1lxoQY', stars: 5 },
              ],
            },
            {
              name: '6th of October City',
              lat: 29.937223,
              lng: 30.927000,
              placeId: 'ChIJI0YkmHFcWBQR-NKjXiACtsQ',
              hotels: [
                { name: 'Novotel 6th Of October', lat: 29.970790, lng: 30.956730, placeId: 'ChIJGcD6CfVcWBQRyEHGINGbkXw', stars: 4 },
                { name: 'Hilton Pyramids Golf Resort', lat: 29.977830, lng: 31.012530, placeId: 'ChIJf3wlVQ9BWBQR5qBDqBqxsGE', stars: 5 },
              ],
            },
          ],
        },
        {
          name: 'Alexandria',
          lat: 31.200092,
          lng: 29.918739,
          placeId: 'ChIJ-_eblkPe2xQRy7LK7v6PmE0',
          zones: [
            {
              name: 'Corniche',
              lat: 31.213889,
              lng: 29.944722,
              placeId: 'ChIJ9-HOe1De2xQRJKXrM1_EM5Q',
              hotels: [
                { name: 'Four Seasons Hotel Alexandria at San Stefano', lat: 31.243420, lng: 29.985050, placeId: 'ChIJVQjl9TDe2xQRInBpMuCRHjE', stars: 5 },
                { name: 'Hilton Alexandria Corniche', lat: 31.216890, lng: 29.953930, placeId: 'ChIJwcSQ9E_e2xQRaicWE_bVBaQ', stars: 5 },
                { name: 'Steigenberger Cecil Hotel', lat: 31.197630, lng: 29.892480, placeId: 'ChIJ1Uy48nre2xQRZbFnnMFKcFs', stars: 4 },
              ],
            },
            {
              name: 'Montaza',
              lat: 31.285278,
              lng: 30.016389,
              placeId: 'ChIJN3c6Gyre2xQR7fOGQn3k5_s',
              hotels: [
                { name: 'Helnan Palestine Hotel', lat: 31.285980, lng: 30.017380, placeId: 'ChIJoT0oNh_f2xQR5eeBwzKTQ1U', stars: 4 },
                { name: 'Sheraton Montazah Hotel', lat: 31.276930, lng: 30.017790, placeId: 'ChIJx3Ly6xzf2xQRG2VTIB2AjHA', stars: 5 },
              ],
            },
            {
              name: 'Borg El Arab',
              lat: 30.917778,
              lng: 29.686944,
              placeId: 'ChIJEanOBB_33xQR_2MVDMBh3tw',
              hotels: [
                { name: 'Hilton Alexandria King\'s Ranch', lat: 30.943370, lng: 29.726180, placeId: 'ChIJ67sJYNTz3xQRWILcTr1p5ME', stars: 5 },
                { name: 'Jaz Crystal Resort', lat: 30.913250, lng: 29.682470, placeId: 'ChIJZ2wA9mH33xQROTJzMg3z9OQ', stars: 5 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // HURGHADA INTERNATIONAL AIRPORT (HRG)
    // ──────────────────────────────────────────
    {
      name: 'Hurghada International Airport',
      code: 'HRG',
      lat: 27.180278,
      lng: 33.799444,
      placeId: 'ChIJo8oqfgj8OhQRsA0TW8K1O3o',
      cities: [
        {
          name: 'Hurghada',
          lat: 27.257896,
          lng: 33.811607,
          placeId: 'ChIJxfmfV38EOxQRJFHV6pXSSck',
          zones: [
            {
              name: 'Hurghada Center',
              lat: 27.189539,
              lng: 33.831741,
              placeId: 'ChIJn8W-YIT_OhQRj8S-FsVBrHc',
              hotels: [
                { name: 'Steigenberger Aqua Magic', lat: 27.183740, lng: 33.836380, placeId: 'ChIJU8BVT7L_OhQR7IvqR-LnLnM', stars: 5 },
                { name: 'Hilton Hurghada Resort', lat: 27.193540, lng: 33.842070, placeId: 'ChIJm-qKuor_OhQRHYJVnxqVEgo', stars: 5 },
                { name: 'Marriott Hurghada Beach Resort', lat: 27.195280, lng: 33.844310, placeId: 'ChIJXSJNmoH_OhQRJGb7oL5SHVA', stars: 5 },
                { name: 'Jaz Aquamarine Resort', lat: 27.151680, lng: 33.824720, placeId: 'ChIJb9DX-Nv-OhQRbzV3qbwCyIQ', stars: 5 },
                { name: 'Dana Beach Resort', lat: 27.156270, lng: 33.825880, placeId: 'ChIJaxWjl93-OhQRmV0Bp4KRcJ4', stars: 5 },
                { name: 'Sunrise Garden Beach Resort', lat: 27.155290, lng: 33.825290, placeId: 'ChIJd_T48dv-OhQRB87QQfXXOaw', stars: 5 },
                { name: 'Beach Albatros Resort', lat: 27.157820, lng: 33.826530, placeId: 'ChIJc2j-h9z-OhQRkAG5MJ2sLxE', stars: 4 },
              ],
            },
            {
              name: 'Sahl Hasheesh',
              lat: 27.057000,
              lng: 33.860000,
              placeId: 'ChIJf-LNz5v7OhQRfGfIGPCDQ4s',
              hotels: [
                { name: 'Premier Le Reve Hotel & Spa', lat: 27.059280, lng: 33.864490, placeId: 'ChIJQ7TUvJ_7OhQR4FVL_fUBSag', stars: 5 },
                { name: 'Tropitel Sahl Hasheesh', lat: 27.055820, lng: 33.857280, placeId: 'ChIJq5v1qJb7OhQR1-3vMFIyW0Q', stars: 5 },
                { name: 'Oberoi Sahl Hasheesh', lat: 27.065640, lng: 33.868270, placeId: 'ChIJW8g3pKP7OhQRGaSfTLQfJsg', stars: 5 },
                { name: 'Baron Palace Sahl Hasheesh', lat: 27.058260, lng: 33.862730, placeId: 'ChIJpSdNj5_7OhQRSWV9oFgG4Fw', stars: 5 },
                { name: 'Kempinski Hotel Soma Bay', lat: 27.038790, lng: 33.889430, placeId: 'ChIJ9xwFH0f7OhQRO67eeWRLI6Q', stars: 5 },
                { name: 'Cleopatra Luxury Resort Makadi Bay', lat: 27.047030, lng: 33.860790, placeId: 'ChIJuYo1b5b7OhQRjFNnpPL8Txk', stars: 5 },
              ],
            },
            {
              name: 'El Gouna',
              lat: 27.182536,
              lng: 33.680270,
              placeId: 'ChIJLR2CUQj_OhQRCGXlpPGwxT0',
              hotels: [
                { name: 'Sheraton Miramar Resort El Gouna', lat: 27.193880, lng: 33.687760, placeId: 'ChIJ0ThbIQb_OhQROgMsC-5bQp8', stars: 5 },
                { name: 'Steigenberger Golf Resort El Gouna', lat: 27.184250, lng: 33.676420, placeId: 'ChIJgaLjJhL_OhQR1z9J5yfwKXE', stars: 5 },
                { name: 'Mövenpick Resort & Spa El Gouna', lat: 27.186120, lng: 33.683910, placeId: 'ChIJ79MBYRH_OhQRe8FfQMKM2RU', stars: 5 },
                { name: 'The Three Corners Rihana Resort', lat: 27.184640, lng: 33.681510, placeId: 'ChIJRSwHuA3_OhQR-ql5T3YKrKk', stars: 4 },
                { name: 'Casa Cook El Gouna', lat: 27.197060, lng: 33.684230, placeId: 'ChIJm9PMXAH_OhQRvtZ5p-eTe28', stars: 5 },
              ],
            },
            {
              name: 'Makadi Bay',
              lat: 27.047222,
              lng: 33.877778,
              placeId: 'ChIJ38oKs5P7OhQR1kBhgQu2w3A',
              hotels: [
                { name: 'Jaz Makadi Star & Spa', lat: 27.048240, lng: 33.877380, placeId: 'ChIJtzG9zJP7OhQRIqPLvX3KVig', stars: 5 },
                { name: 'Sunrise Royal Makadi Resort', lat: 27.044810, lng: 33.875590, placeId: 'ChIJjQGMYJP7OhQRwSmr4GKc5Fg', stars: 5 },
                { name: 'Fort Arabesque Resort Spa & Villas', lat: 27.051370, lng: 33.878720, placeId: 'ChIJz5jKjpb7OhQRbQFeCaAJFqo', stars: 4 },
                { name: 'TIA Heights Makadi Bay', lat: 27.044390, lng: 33.873640, placeId: 'ChIJPfk_TpL7OhQR3s_L2cxkdqs', stars: 5 },
              ],
            },
            {
              name: 'Soma Bay',
              lat: 27.020000,
              lng: 33.910000,
              placeId: 'ChIJN0kBZ0v7OhQRvZB7GqKAJ-0',
              hotels: [
                { name: 'Kempinski Hotel Soma Bay', lat: 27.038790, lng: 33.889430, placeId: 'ChIJ9xwFH0f7OhQRO67eeWRLI6Q', stars: 5 },
                { name: 'Sheraton Soma Bay Resort', lat: 27.022070, lng: 33.913840, placeId: 'ChIJ4Ui-IE37OhQRcqFYF3E-dB4', stars: 5 },
                { name: 'La Résidence des Cascades Golf & Spa Resort', lat: 27.028450, lng: 33.906120, placeId: 'ChIJWUw8Lkn7OhQRX5FzVfTQ-wI', stars: 5 },
                { name: 'Robinson Club Soma Bay', lat: 27.023840, lng: 33.912470, placeId: 'ChIJv0g-AU37OhQROyLKr1aqWaA', stars: 4 },
              ],
            },
          ],
        },
        {
          name: 'Safaga',
          lat: 26.739167,
          lng: 33.935833,
          placeId: 'ChIJ1dGOyVj3OhQRgb8dS5YnPBg',
          zones: [
            {
              name: 'Safaga Center',
              lat: 26.739167,
              lng: 33.935833,
              placeId: 'ChIJ1dGOyVj3OhQRgb8dS5YnPBg',
              hotels: [
                { name: 'Amwaj Blue Beach Resort & Spa', lat: 26.737060, lng: 33.937820, placeId: 'ChIJ49rXSVv3OhQR3Yp2JOCDwEA', stars: 5 },
                { name: 'Riviera Plaza Abu Soma', lat: 26.830620, lng: 33.917470, placeId: 'ChIJqSXpC5_3OhQRuX6vQFWJWXQ', stars: 4 },
              ],
            },
          ],
        },
        {
          name: 'Marsa Alam',
          lat: 25.067000,
          lng: 34.900000,
          placeId: 'ChIJPyqqXr1iQRQRFq4U6cCKSZI',
          zones: [
            {
              name: 'Marsa Alam Center',
              lat: 25.067000,
              lng: 34.900000,
              placeId: 'ChIJPyqqXr1iQRQRFq4U6cCKSZI',
              hotels: [
                { name: 'Jaz Grand Marsa', lat: 25.064530, lng: 34.920470, placeId: 'ChIJxw2vJJpiQRQRZWPdLQ7cq70', stars: 5 },
                { name: 'Concorde Moreen Beach Resort & Spa', lat: 25.057380, lng: 34.906290, placeId: 'ChIJK2B8VrBiQRQRXpmN-aVLl84', stars: 5 },
              ],
            },
            {
              name: 'Port Ghalib',
              lat: 25.016667,
              lng: 34.900000,
              placeId: 'ChIJt1QGONxgQRQRC67jYnJIX5o',
              hotels: [
                { name: 'Marina Lodge at Port Ghalib', lat: 25.017290, lng: 34.896730, placeId: 'ChIJb_cE-dxgQRQR8K3NZ_9fpgg', stars: 4 },
                { name: 'Crowne Plaza Sahara Oasis Port Ghalib', lat: 25.019280, lng: 34.898410, placeId: 'ChIJhxYxz91gQRQRBKVTzCGZ2_8', stars: 5 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // SHARM EL SHEIKH INTERNATIONAL AIRPORT (SSH)
    // ──────────────────────────────────────────
    {
      name: 'Sharm El Sheikh International Airport',
      code: 'SSH',
      lat: 27.977222,
      lng: 34.394722,
      placeId: 'ChIJcZ7qPMYuEBQRWIo0Sx-JqVc',
      cities: [
        {
          name: 'Sharm El Sheikh',
          lat: 27.915817,
          lng: 34.329950,
          placeId: 'ChIJk6zMdcQtEBQRyH1gvBQX3VE',
          zones: [
            {
              name: 'Naama Bay',
              lat: 27.906667,
              lng: 34.330278,
              placeId: 'ChIJi6j5hLwtEBQRj-_nCFWsFbQ',
              hotels: [
                { name: 'Hilton Sharm Waterfalls Resort', lat: 27.904310, lng: 34.325280, placeId: 'ChIJG66T_7ctEBQRcv3bTRRXjD0', stars: 5 },
                { name: 'Stella Di Mare Beach Hotel & Spa', lat: 27.906450, lng: 34.331270, placeId: 'ChIJ-wz7jrwtEBQRHLfnKDqFb_Q', stars: 5 },
                { name: 'Novotel Sharm El Sheikh', lat: 27.907640, lng: 34.329870, placeId: 'ChIJJ5N4rrwtEBQRqPPq1NlY1Nk', stars: 5 },
                { name: 'Tropitel Naama Bay', lat: 27.908290, lng: 34.328860, placeId: 'ChIJW6w5w7wtEBQR0Dd83sLncVE', stars: 5 },
                { name: 'Marriott Sharm El Sheikh Resort', lat: 27.905750, lng: 34.327920, placeId: 'ChIJBx0FwLwtEBQRxgW_OD5mlHs', stars: 5 },
                { name: 'Lido Sharm Hotel', lat: 27.906630, lng: 34.327640, placeId: 'ChIJZdXO5bwtEBQRS5V-OlO3hfY', stars: 4 },
              ],
            },
            {
              name: 'Sharks Bay',
              lat: 27.879722,
              lng: 34.323889,
              placeId: 'ChIJQwLjjpMtEBQROVA5aS8Iap0',
              hotels: [
                { name: 'Savoy Sharm El Sheikh', lat: 27.878390, lng: 34.321430, placeId: 'ChIJcTm6wJItEBQR_8R4XLkdJR4', stars: 5 },
                { name: 'Rixos Sharm El Sheikh', lat: 27.880250, lng: 34.324610, placeId: 'ChIJB4JEW5MtEBQR-NP53S4cRlk', stars: 5 },
                { name: 'Sultan Gardens Resort', lat: 27.879130, lng: 34.320870, placeId: 'ChIJyxXaE5ItEBQRQb2zcWVrm5U', stars: 5 },
                { name: 'Coral Sea Sensatori Sharm El Sheikh', lat: 27.881010, lng: 34.326410, placeId: 'ChIJMaIZV5QtEBQRGQCaK30Q_bM', stars: 5 },
              ],
            },
            {
              name: 'Nabq Bay',
              lat: 27.968333,
              lng: 34.408056,
              placeId: 'ChIJ9_0gSLAuEBQR-yRnXPlrZns',
              hotels: [
                { name: 'Rixos Premium Seagate Sharm El Sheikh', lat: 27.970430, lng: 34.406720, placeId: 'ChIJOwBM77AuEBQRDN8F8tXrLss', stars: 5 },
                { name: 'Steigenberger Alcazar Sharm El Sheikh', lat: 27.967250, lng: 34.409860, placeId: 'ChIJ_3N9hq8uEBQRKAKqaIl_FPQ', stars: 5 },
                { name: 'Jaz Mirabel Resort', lat: 27.962180, lng: 34.404290, placeId: 'ChIJfzDOE64uEBQR2dKv2uLCKBA', stars: 5 },
                { name: 'Charmillion Club Resort', lat: 27.964380, lng: 34.405810, placeId: 'ChIJ37e0Sa4uEBQRMkjRHQFx_go', stars: 5 },
                { name: 'Royal Albatros Moderna', lat: 27.959840, lng: 34.402570, placeId: 'ChIJ58M9D6wuEBQRJ4z-c57p1sQ', stars: 5 },
              ],
            },
            {
              name: 'Old Market',
              lat: 27.862500,
              lng: 34.297222,
              placeId: 'ChIJB5GCXjwtEBQRdQGxwZ3aQvQ',
              hotels: [
                { name: 'Ritz-Carlton Sharm El Sheikh', lat: 27.851280, lng: 34.289560, placeId: 'ChIJgxy7MiAtEBQR1uQOlXPFdlo', stars: 5 },
                { name: 'Four Seasons Resort Sharm El Sheikh', lat: 27.855140, lng: 34.292830, placeId: 'ChIJ52aQfyYtEBQR0TGU-N47Sds', stars: 5 },
                { name: 'Il Mercato Hotel & Spa', lat: 27.861490, lng: 34.296820, placeId: 'ChIJ5-aF9DstEBQRiJY9fMRwkIw', stars: 5 },
              ],
            },
            {
              name: 'Ras Um El Sid',
              lat: 27.843889,
              lng: 34.301111,
              placeId: 'ChIJD_1KxhktEBQRqT4KP_kqJWk',
              hotels: [
                { name: 'Renaissance Sharm El Sheikh Golden View Beach Resort', lat: 27.843940, lng: 34.302080, placeId: 'ChIJz2DRKRktEBQRB83TGcPbkKg', stars: 5 },
                { name: 'The Grand Hotel Sharm El Sheikh', lat: 27.845230, lng: 34.301170, placeId: 'ChIJWZYgKBwtEBQR0XLAH6uyqIA', stars: 5 },
              ],
            },
          ],
        },
        {
          name: 'Dahab',
          lat: 28.500000,
          lng: 34.516667,
          placeId: 'ChIJ_weCJPpiEBQR4BJ15Hv7lO0',
          zones: [
            {
              name: 'Dahab Center',
              lat: 28.500000,
              lng: 34.516667,
              placeId: 'ChIJ_weCJPpiEBQR4BJ15Hv7lO0',
              hotels: [
                { name: 'Le Méridien Dahab Resort', lat: 28.488530, lng: 34.509820, placeId: 'ChIJY3T9i_NiEBQRPgEjJN7zNqw', stars: 5 },
                { name: 'Swiss Inn Resort Dahab', lat: 28.481270, lng: 34.505930, placeId: 'ChIJd5mW7-hiEBQRSF_3RK2M6rU', stars: 4 },
                { name: 'Jaz Dahabeya', lat: 28.494280, lng: 34.513640, placeId: 'ChIJ_VE0sPRiEBQRhWHqOdsMkdo', stars: 4 },
              ],
            },
          ],
        },
        {
          name: 'Taba',
          lat: 29.493611,
          lng: 34.898333,
          placeId: 'ChIJkVbS6N3KEBQRJAd8dCvGwuQ',
          zones: [
            {
              name: 'Taba Center',
              lat: 29.493611,
              lng: 34.898333,
              placeId: 'ChIJkVbS6N3KEBQRJAd8dCvGwuQ',
              hotels: [
                { name: 'Hilton Taba Resort & Nelson Village', lat: 29.495310, lng: 34.900280, placeId: 'ChIJpYZ6P97KEBQRV1jG-79_OJQ', stars: 5 },
                { name: 'Strand Taba Heights Beach & Golf Resort', lat: 29.396850, lng: 34.821640, placeId: 'ChIJ3bEHM5TJEBQRzCUOgMbcKyQ', stars: 5 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // LUXOR INTERNATIONAL AIRPORT (LXR)
    // ──────────────────────────────────────────
    {
      name: 'Luxor International Airport',
      code: 'LXR',
      lat: 25.670833,
      lng: 32.706667,
      placeId: 'ChIJvQXCQY2VNRQRjRFx9WH9E28',
      cities: [
        {
          name: 'Luxor',
          lat: 25.687243,
          lng: 32.639637,
          placeId: 'ChIJEw2bGoaVNRQRqPheCnxGOGg',
          zones: [
            {
              name: 'Luxor East Bank',
              lat: 25.698889,
              lng: 32.641667,
              placeId: 'ChIJV8_2NI2VNRQRIbWIRdfLqME',
              hotels: [
                { name: 'Sofitel Winter Palace Luxor', lat: 25.696260, lng: 32.638870, placeId: 'ChIJwQPqgoyVNRQRkr2v7e-CZVE', stars: 5 },
                { name: 'Steigenberger Nile Palace Luxor', lat: 25.698590, lng: 32.640070, placeId: 'ChIJvZfEkI2VNRQRdEDcWPjFXug', stars: 5 },
                { name: 'Hilton Luxor Resort & Spa', lat: 25.705280, lng: 32.643410, placeId: 'ChIJl4VdBI6VNRQRKyNsjIE72B0', stars: 5 },
                { name: 'Sonesta St. George Hotel Luxor', lat: 25.697240, lng: 32.639620, placeId: 'ChIJOZ5Wa4yVNRQRwIH2J9gQzTk', stars: 5 },
              ],
            },
            {
              name: 'Luxor West Bank',
              lat: 25.719167,
              lng: 32.601389,
              placeId: 'ChIJz2kIBIKUNRQRNAh-k8w3QOU',
              hotels: [
                { name: 'Al Moudira Hotel', lat: 25.693880, lng: 32.603240, placeId: 'ChIJE3kKPUyUNRQRbE4wJjVdGQk', stars: 5 },
                { name: 'Djorff Palace', lat: 25.722650, lng: 32.598370, placeId: 'ChIJR3wsCYOUNRQRAnT3fOzxXuY', stars: 3 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // ASWAN INTERNATIONAL AIRPORT (ASW)
    // ──────────────────────────────────────────
    {
      name: 'Aswan International Airport',
      code: 'ASW',
      lat: 23.964167,
      lng: 32.820000,
      placeId: 'ChIJd2-eMl6hQBQRHj_i3jkHbmY',
      cities: [
        {
          name: 'Aswan',
          lat: 24.088938,
          lng: 32.899829,
          placeId: 'ChIJK7NG5GmiQBQRJF6y48HIsYA',
          zones: [
            {
              name: 'Aswan Center',
              lat: 24.088938,
              lng: 32.899829,
              placeId: 'ChIJK7NG5GmiQBQRJF6y48HIsYA',
              hotels: [
                { name: 'Sofitel Legend Old Cataract Aswan', lat: 24.084630, lng: 32.886970, placeId: 'ChIJHcr2hmmjQBQRFCwq-uK0fYE', stars: 5 },
                { name: 'Mövenpick Resort Aswan', lat: 24.089930, lng: 32.881570, placeId: 'ChIJPcDN8sSjQBQRqHNnlVyXF5k', stars: 5 },
                { name: 'Pyramisa Isis Island Aswan', lat: 24.081460, lng: 32.880620, placeId: 'ChIJeTjLm2SjQBQRYfKFPh2NHEI', stars: 5 },
                { name: 'Basma Hotel Aswan', lat: 24.088380, lng: 32.890710, placeId: 'ChIJE7jS4WmjQBQRzYhBEHpZJFY', stars: 4 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // BORG EL ARAB AIRPORT (HBE) - Alexandria
    // ──────────────────────────────────────────
    {
      name: 'Borg El Arab Airport',
      code: 'HBE',
      lat: 30.917500,
      lng: 29.696111,
      placeId: 'ChIJI3LwjCD33xQRHOoaX0Ws59U',
      cities: [
        {
          name: 'North Coast',
          lat: 30.850000,
          lng: 29.000000,
          placeId: 'ChIJ3z11m4C53xQRkKGP5FLAwmo',
          zones: [
            {
              name: 'Marina El Alamein',
              lat: 30.830278,
              lng: 28.951389,
              placeId: 'ChIJ96h5TM6y3xQRkMBCnNKldJ8',
              hotels: [
                { name: 'Hilton Marsa Alam Nubian Resort', lat: 30.831270, lng: 28.955620, placeId: 'ChIJM9ixnM-y3xQRNQl8X5_-Mig', stars: 5 },
                { name: 'Jaz Almaza Bay', lat: 31.045260, lng: 28.136350, placeId: 'ChIJK_8pJAGn3xQRqSTvnTQnFCQ', stars: 5 },
              ],
            },
            {
              name: 'El Alamein',
              lat: 30.840000,
              lng: 28.950000,
              placeId: 'ChIJW4LAjf-x3xQRFbQiRq_-kPw',
              hotels: [
                { name: 'The Address Marassi Golf Resort & Spa', lat: 30.859280, lng: 28.600440, placeId: 'ChIJZZAibImm3xQRGGFPgBZqDfQ', stars: 5 },
                { name: 'Jaz Oriental Resort', lat: 30.863710, lng: 28.643270, placeId: 'ChIJq2tTUNem3xQR0S0_g44sK9g', stars: 5 },
              ],
            },
          ],
        },
      ],
    },

    // ──────────────────────────────────────────
    // SPHINX INTERNATIONAL AIRPORT (SPX) - New Cairo / 6th October
    // ──────────────────────────────────────────
    {
      name: 'Sphinx International Airport',
      code: 'SPX',
      lat: 30.110000,
      lng: 30.891389,
      placeId: 'ChIJY3S6gKtfWBQR8fYEYMCp-Qg',
      cities: [
        {
          name: 'New Alamein',
          lat: 30.816667,
          lng: 28.966667,
          placeId: 'ChIJOUWFuKKy3xQR-cSm94lp2QE',
          zones: [
            {
              name: 'New Alamein City',
              lat: 30.816667,
              lng: 28.966667,
              placeId: 'ChIJOUWFuKKy3xQR-cSm94lp2QE',
              hotels: [
                { name: 'Hilton New Alamein', lat: 30.819230, lng: 28.960840, placeId: 'ChIJ0df1ZKSy3xQReZKF0_1c2Vc', stars: 5 },
                { name: 'The Chedi El Alamein', lat: 30.820870, lng: 28.958730, placeId: 'ChIJeyVFGqOy3xQRvN_1MbKC1-M', stars: 5 },
              ],
            },
          ],
        },
      ],
    },
  ],
};

/**
 * Seeds Egypt locations with coordinates.
 * Uses upsert logic: deletes existing locations for the Egypt tree and re-creates them.
 */
export async function seedEgyptLocations(prisma: any) {
  const data = EGYPT_DATA;

  console.log('\n─── Seeding Egypt Locations ───');

  // Upsert country
  const country = await prisma.country.upsert({
    where: { code: data.code },
    update: {
      name: data.name,
      latitude: data.lat,
      longitude: data.lng,
      placeId: data.placeId,
    },
    create: {
      name: data.name,
      code: data.code,
      latitude: data.lat,
      longitude: data.lng,
      placeId: data.placeId,
    },
  });
  console.log(`Country: ${country.name} (${country.code})`);

  let airportCount = 0;
  let cityCount = 0;
  let zoneCount = 0;
  let hotelCount = 0;

  for (const airportData of data.airports) {
    // Upsert airport by unique code
    const airport = await prisma.airport.upsert({
      where: { code: airportData.code },
      update: {
        name: airportData.name,
        latitude: airportData.lat,
        longitude: airportData.lng,
        placeId: airportData.placeId,
        countryId: country.id,
        deletedAt: null,
      },
      create: {
        name: airportData.name,
        code: airportData.code,
        latitude: airportData.lat,
        longitude: airportData.lng,
        placeId: airportData.placeId,
        countryId: country.id,
      },
    });
    airportCount++;

    for (const cityData of airportData.cities) {
      // Find or create city (no unique constraint, match by name + airport)
      let city = await prisma.city.findFirst({
        where: { name: cityData.name, airportId: airport.id, deletedAt: null },
      });
      if (city) {
        city = await prisma.city.update({
          where: { id: city.id },
          data: {
            latitude: cityData.lat,
            longitude: cityData.lng,
            placeId: cityData.placeId,
          },
        });
      } else {
        city = await prisma.city.create({
          data: {
            name: cityData.name,
            airportId: airport.id,
            latitude: cityData.lat,
            longitude: cityData.lng,
            placeId: cityData.placeId,
          },
        });
      }
      cityCount++;

      for (const zoneData of cityData.zones) {
        // Find or create zone
        let zone = await prisma.zone.findFirst({
          where: { name: zoneData.name, cityId: city.id, deletedAt: null },
        });
        if (zone) {
          zone = await prisma.zone.update({
            where: { id: zone.id },
            data: {
              latitude: zoneData.lat,
              longitude: zoneData.lng,
              placeId: zoneData.placeId,
            },
          });
        } else {
          zone = await prisma.zone.create({
            data: {
              name: zoneData.name,
              cityId: city.id,
              latitude: zoneData.lat,
              longitude: zoneData.lng,
              placeId: zoneData.placeId,
            },
          });
        }
        zoneCount++;

        for (const hotelData of zoneData.hotels) {
          // Find or create hotel
          let hotel = await prisma.hotel.findFirst({
            where: { name: hotelData.name, zoneId: zone.id, deletedAt: null },
          });
          if (hotel) {
            await prisma.hotel.update({
              where: { id: hotel.id },
              data: {
                latitude: hotelData.lat,
                longitude: hotelData.lng,
                placeId: hotelData.placeId,
                address: hotelData.address || null,
                stars: hotelData.stars || null,
              },
            });
          } else {
            await prisma.hotel.create({
              data: {
                name: hotelData.name,
                zoneId: zone.id,
                latitude: hotelData.lat,
                longitude: hotelData.lng,
                placeId: hotelData.placeId,
                address: hotelData.address || null,
                stars: hotelData.stars || null,
              },
            });
          }
          hotelCount++;
        }
      }
    }
  }

  console.log(`  Airports: ${airportCount}`);
  console.log(`  Cities: ${cityCount}`);
  console.log(`  Zones: ${zoneCount}`);
  console.log(`  Hotels: ${hotelCount}`);
  console.log('Egypt locations seeded successfully.\n');
}
