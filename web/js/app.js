/**
 * ARES-1 Mars Rover — 3D Cinematic Simulation Application
 * Powered by Three.js WebGL, Procedural Shaders, and Web Audio API
 */

// ============================================================================
// 1. SYNTHESIZED WEB AUDIO ENGINE (Zero external sound dependencies)
// ============================================================================
class MarsSoundEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
    this.motorOsc = null;
    this.motorGain = null;
    this.windGain = null;
  }

  init() {
    if (this.ctx) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
      this._startAmbientWind();
      this._setupMotorSynth();
    } catch (e) {
      console.warn("Web Audio API not supported", e);
    }
  }

  toggle() {
    this.enabled = !this.enabled;
    if (this.ctx) {
      if (this.enabled) {
        this.ctx.resume();
        if (this.windGain) this.windGain.gain.setValueAtTime(0.08, this.ctx.currentTime);
      } else {
        if (this.windGain) this.windGain.gain.setValueAtTime(0.0, this.ctx.currentTime);
        if (this.motorGain) this.motorGain.gain.setValueAtTime(0.0, this.ctx.currentTime);
      }
    }
    return this.enabled;
  }

  _startAmbientWind() {
    if (!this.ctx) return;
    const bufferSize = this.ctx.sampleRate * 2;
    const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1;
    }

    const whiteNoise = this.ctx.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 350;
    filter.Q.value = 3.0;

    this.windGain = this.ctx.createGain();
    this.windGain.gain.value = this.enabled ? 0.08 : 0.0;

    whiteNoise.connect(filter);
    filter.connect(this.windGain);
    this.windGain.connect(this.ctx.destination);
    whiteNoise.start(0);
  }

  _setupMotorSynth() {
    if (!this.ctx) return;
    this.motorOsc = this.ctx.createOscillator();
    this.motorOsc.type = "sawtooth";
    this.motorOsc.frequency.value = 65;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 220;

    this.motorGain = this.ctx.createGain();
    this.motorGain.gain.value = 0.0;

    this.motorOsc.connect(filter);
    filter.connect(this.motorGain);
    this.motorGain.connect(this.ctx.destination);
    this.motorOsc.start(0);
  }

  setMotorRunning(running, speedMult = 1.0) {
    if (!this.ctx || !this.enabled || !this.motorGain) return;
    const now = this.ctx.currentTime;
    if (running) {
      this.motorOsc.frequency.setValueAtTime(60 + speedMult * 20, now);
      this.motorGain.gain.setTargetAtTime(0.06, now, 0.1);
    } else {
      this.motorGain.gain.setTargetAtTime(0.0, now, 0.1);
    }
  }

  playSonarPing() {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(1100, now);
    osc.frequency.exponentialRampToValueAtTime(700, now + 0.25);

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.25);
  }

  playHazardKlaxon() {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    [440, 880].forEach((freq, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "square";
      osc.frequency.setValueAtTime(freq, now + i * 0.1);
      gain.gain.setValueAtTime(0.09, now + i * 0.1);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.1 + 0.12);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now + i * 0.1);
      osc.stop(now + i * 0.1 + 0.12);
    });
  }

  playVictoryChime() {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    notes.forEach((freq, i) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + i * 0.12);
      gain.gain.setValueAtTime(0.18, now + i * 0.12);
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.12 + 0.6);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now + i * 0.12);
      osc.stop(now + i * 0.12 + 0.6);
    });
  }

  playClick() {
    if (!this.ctx || !this.enabled) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(800, now);
    gain.gain.setValueAtTime(0.05, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.04);
  }
}

// Global Audio Engine Instance
const soundEngine = new MarsSoundEngine();


// ============================================================================
// 2. MAIN 3D APPLICATION & SIMULATION CONTROLLER
// ============================================================================
class MarsRover3DApp {
  constructor() {
    this.container = document.getElementById("canvas-container");
    this.gridSize = 6;
    this.cellSize = 12.0; // 3D units per grid cell
    this.gridOriginX = -((this.gridSize - 1) * this.cellSize) / 2;
    this.gridOriginZ = -((this.gridSize - 1) * this.cellSize) / 2;

    // Simulation State
    this.isPaused = false;
    this.isFinished = false;
    this.speedMultiplier = 1.0;
    this.baseStepDelay = 1.2; // seconds
    this.lastStepTime = performance.now() / 1000;
    this.cameraMode = "chase"; // 'chase', 'satellite', 'mast', 'orbit'
    this.showDebugGrid = false;

    // 3D Scene Components
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.orbitControls = null;

    // Entity References
    this.roverGroup = null;
    this.roverWheels = [];
    this.roverHeadlights = [];
    this.roverMastHead = null;
    this.sonarPulseMesh = null;
    this.terrainMesh = null;
    this.gridLinesGroup = null;
    this.fogBlocks = new Map(); // key "x,y" -> Mesh
    this.hazardMeshes = new Map();
    this.radiationMeshes = new Map();
    this.visitedMarkers = new Map();
    this.tireTracksLine = null;
    this.tireTrackPoints = [];
    this.dustParticles = [];

    // Animation Lerp
    this.roverPosCurrent = new THREE.Vector3(0, 0, 0);
    this.roverPosTarget = new THREE.Vector3(0, 0, 0);
    this.roverTargetHeading = 0.0;
    this.roverCurrentHeading = 0.0;
    this.moveProgress = 1.0;
    this.moveSpeed = 3.5;

    // Backtrack Waypoints
    this.animationQueue = [];

    // Telemetry Cache
    this.latestTelemetry = null;
    this.solvablePathLength = 0;

    // Boot
    this._initThree();
    this._initLights();
    this._initTerrain();
    this._initSkyAndAtmosphere();
    this._initRover();
    this._initUIEvents();
    this._fetchInitState();

    // Start Render Loop
    this.clock = new THREE.Clock();
    requestAnimationFrame((t) => this._animate(t));
  }

  // --------------------------------------------------------------------------
  // Scene & Engine Setup
  // --------------------------------------------------------------------------
  _initThree() {
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x3a180e, 0.009);

    const aspect = window.innerWidth / window.innerHeight;
    this.camera = new THREE.PerspectiveCamera(50, aspect, 0.5, 500);
    this.camera.position.set(0, 30, 45);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    this.container.appendChild(this.renderer.domElement);

    this.orbitControls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.orbitControls.enableDamping = true;
    this.orbitControls.dampingFactor = 0.05;
    this.orbitControls.maxPolarAngle = Math.PI / 2 - 0.05;
    this.orbitControls.minDistance = 5;
    this.orbitControls.maxDistance = 180;
    this.orbitControls.enabled = false; // default chase cam

    window.addEventListener("resize", () => {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    });
  }

  _initLights() {
    const ambient = new THREE.AmbientLight(0x7a3d24, 1.1);
    this.scene.add(ambient);

    // Warm Martian Sunlight
    const sunLight = new THREE.DirectionalLight(0xffecd2, 2.4);
    sunLight.position.set(45, 75, 50);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 200;
    const d = 60;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    sunLight.shadow.bias = -0.0005;
    this.scene.add(sunLight);

    // Subtle blue fill light from upper space
    const spaceFill = new THREE.DirectionalLight(0x38527a, 0.6);
    spaceFill.position.set(-30, 40, -40);
    this.scene.add(spaceFill);
  }

  _initSkyAndAtmosphere() {
    // Large Sky Dome
    const skyGeo = new THREE.SphereGeometry(300, 32, 16);
    const skyMat = new THREE.MeshBasicMaterial({
      color: 0x481c0e,
      side: THREE.BackSide,
    });
    const skyMesh = new THREE.Mesh(skyGeo, skyMat);
    this.scene.add(skyMesh);

    // Atmospheric Dust Particles
    const dustGeo = new THREE.BufferGeometry();
    const dustCount = 800;
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount * 3; i += 3) {
      dustPos[i] = (Math.random() - 0.5) * 160;
      dustPos[i + 1] = Math.random() * 40;
      dustPos[i + 2] = (Math.random() - 0.5) * 160;
    }
    dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({
      color: 0xdf7238,
      size: 0.5,
      transparent: true,
      opacity: 0.5,
    });
    this.dustSystem = new THREE.Points(dustGeo, dustMat);
    this.scene.add(this.dustSystem);
  }

  _initTerrain() {
    const terrainWidth = this.gridSize * this.cellSize + 60;
    const terrainGeo = new THREE.PlaneGeometry(terrainWidth, terrainWidth, 96, 96);
    terrainGeo.rotateX(-Math.PI / 2);

    // Procedural Dune & Crater Displacement
    const pos = terrainGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const vx = pos.getX(i);
      const vz = pos.getZ(i);
      // Gentle rolling dunes
      let h = Math.sin(vx * 0.08) * Math.cos(vz * 0.08) * 0.9;
      h += Math.sin(vx * 0.03 + vz * 0.03) * 1.5;
      // Flatten grid area slightly so rover drives smoothly
      const distFromCenter = Math.sqrt(vx * vx + vz * vz);
      if (distFromCenter < (this.gridSize * this.cellSize) * 0.6) {
        h *= 0.35;
      }
      pos.setY(i, h);
    }
    terrainGeo.computeVertexNormals();

    const terrainMat = new THREE.MeshStandardMaterial({
      color: 0xb5461c,
      roughness: 0.92,
      metalness: 0.08,
      flatShading: false,
    });

    this.terrainMesh = new THREE.Mesh(terrainGeo, terrainMat);
    this.terrainMesh.receiveShadow = true;
    this.scene.add(this.terrainMesh);

    // Scattered 3D Rock Boulders
    this._generateRocks();

    // Debug Grid Lines Group
    this.gridLinesGroup = new THREE.Group();
    const halfGrid = (this.gridSize * this.cellSize) / 2;
    for (let i = 0; i <= this.gridSize; i++) {
      const coord = -halfGrid + i * this.cellSize;
      // Z lines
      const lineGeoZ = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(coord, 0.1, -halfGrid),
        new THREE.Vector3(coord, 0.1, halfGrid),
      ]);
      const lineGeoX = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-halfGrid, 0.1, coord),
        new THREE.Vector3(halfGrid, 0.1, coord),
      ]);
      const lineMat = new THREE.LineBasicMaterial({ color: 0x40c8e0, transparent: true, opacity: 0.35 });
      this.gridLinesGroup.add(new THREE.Line(lineGeoZ, lineMat));
      this.gridLinesGroup.add(new THREE.Line(lineGeoX, lineMat));
    }
    this.gridLinesGroup.visible = this.showDebugGrid;
    this.scene.add(this.gridLinesGroup);
  }

  _generateRocks() {
    const rockGeo = new THREE.DodecahedronGeometry(1.0, 1);
    const rockMat = new THREE.MeshStandardMaterial({ color: 0x6e2c14, roughness: 0.95 });
    const count = 75;
    for (let i = 0; i < count; i++) {
      const rock = new THREE.Mesh(rockGeo, rockMat);
      const angle = Math.random() * Math.PI * 2;
      const rad = 25 + Math.random() * 45;
      rock.position.set(Math.cos(angle) * rad, 0.2, Math.sin(angle) * rad);
      const s = 0.5 + Math.random() * 2.0;
      rock.scale.set(s, s * (0.6 + Math.random() * 0.8), s);
      rock.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
      rock.castShadow = true;
      rock.receiveShadow = true;
      this.scene.add(rock);
    }
  }

  // --------------------------------------------------------------------------
  // 3D Mars Rover Model Construction
  // --------------------------------------------------------------------------
  _initRover() {
    this.roverGroup = new THREE.Group();

    // 1. Main Avionics Chassis Box
    const bodyGeo = new THREE.BoxGeometry(3.2, 1.2, 2.2);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0xdedcd7, // NASA warm white/gold foil
      roughness: 0.4,
      metalness: 0.6,
    });
    const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
    bodyMesh.position.y = 1.3;
    bodyMesh.castShadow = true;
    this.roverGroup.add(bodyMesh);

    // Dark chassis underside
    const underGeo = new THREE.BoxGeometry(3.0, 0.4, 2.0);
    const underMat = new THREE.MeshStandardMaterial({ color: 0x22262c, roughness: 0.8 });
    const underMesh = new THREE.Mesh(underGeo, underMat);
    underMesh.position.y = 0.8;
    this.roverGroup.add(underMesh);

    // 2. Solar Panel Array on Top Deck
    const solarGeo = new THREE.BoxGeometry(2.6, 0.08, 1.8);
    const solarMat = new THREE.MeshStandardMaterial({
      color: 0x142036, // Deep photovoltaic navy
      roughness: 0.2,
      metalness: 0.9,
    });
    const solarMesh = new THREE.Mesh(solarGeo, solarMat);
    solarMesh.position.set(0, 1.95, 0);
    this.roverGroup.add(solarMesh);

    // 3. Sensor Mast & Pan-Tilt Camera Head (MastCam)
    const mastNeckGeo = new THREE.CylinderGeometry(0.08, 0.08, 1.4, 8);
    const mastNeckMat = new THREE.MeshStandardMaterial({ color: 0x333842, metalness: 0.8 });
    const mastNeck = new THREE.Mesh(mastNeckGeo, mastNeckMat);
    mastNeck.position.set(1.1, 2.5, 0);
    this.roverGroup.add(mastNeck);

    this.roverMastHead = new THREE.Group();
    const headGeo = new THREE.BoxGeometry(0.5, 0.35, 0.6);
    const headMat = new THREE.MeshStandardMaterial({ color: 0x22262e, metalness: 0.7 });
    const headMesh = new THREE.Mesh(headGeo, headMat);
    this.roverMastHead.add(headMesh);

    // Dual Glowing Camera Lenses
    [-0.15, 0.15].forEach((zOff) => {
      const eyeGeo = new THREE.CylinderGeometry(0.09, 0.09, 0.2, 12);
      eyeGeo.rotateZ(Math.PI / 2);
      const eyeMat = new THREE.MeshBasicMaterial({ color: 0x40c8e0 });
      const eyeMesh = new THREE.Mesh(eyeGeo, eyeMat);
      eyeMesh.position.set(0.26, 0, zOff);
      this.roverMastHead.add(eyeMesh);
    });

    this.roverMastHead.position.set(1.1, 3.2, 0);
    this.roverGroup.add(this.roverMastHead);

    // 4. UHF High-Gain Antenna Dish
    const dishGeo = new THREE.CylinderGeometry(0.4, 0.1, 0.15, 12);
    dishGeo.rotateZ(Math.PI / 3);
    const dishMat = new THREE.MeshStandardMaterial({ color: 0xdedcd7, metalness: 0.9 });
    const dish = new THREE.Mesh(dishGeo, dishMat);
    dish.position.set(-1.0, 2.3, 0.6);
    this.roverGroup.add(dish);

    // 5. 6 All-Terrain Treaded Wheels (3 on each side)
    const wheelPositions = [
      [-1.2, 0.55, -1.4], [0.0, 0.55, -1.4], [1.2, 0.55, -1.4],
      [-1.2, 0.55, 1.4],  [0.0, 0.55, 1.4],  [1.2, 0.55, 1.4]
    ];
    this.roverWheels = [];

    wheelPositions.forEach(([wx, wy, wz], idx) => {
      const wheelGroup = new THREE.Group();
      wheelGroup.position.set(wx, wy, wz);

      const wGeo = new THREE.CylinderGeometry(0.55, 0.55, 0.45, 16);
      wGeo.rotateX(Math.PI / 2);
      const wMat = new THREE.MeshStandardMaterial({
        color: 0x181a1e, // Deep rubber/graphite
        roughness: 0.9,
      });
      const wMesh = new THREE.Mesh(wGeo, wMat);
      wMesh.castShadow = true;
      wheelGroup.add(wMesh);

      // Wheel Rim
      const rimGeo = new THREE.CylinderGeometry(0.28, 0.28, 0.47, 8);
      rimGeo.rotateX(Math.PI / 2);
      const rimMat = new THREE.MeshStandardMaterial({ color: 0x8a929e, metalness: 0.9 });
      wheelGroup.add(new THREE.Mesh(rimGeo, rimMat));

      this.roverGroup.add(wheelGroup);
      this.roverWheels.push({ group: wheelGroup, mesh: wMesh, isSteering: idx === 0 || idx === 2 || idx === 3 || idx === 5 });
    });

    // 6. Dual LED Spotlight Headlights
    [-0.7, 0.7].forEach((zOff) => {
      const spot = new THREE.SpotLight(0xffffff, 3.5, 30, Math.PI / 5, 0.3, 1.5);
      spot.position.set(1.6, 1.2, zOff);
      spot.target.position.set(8.0, 0.2, zOff);
      spot.castShadow = true;
      spot.shadow.mapSize.width = 512;
      spot.shadow.mapSize.height = 512;
      this.roverGroup.add(spot);
      this.roverGroup.add(spot.target);
      this.roverHeadlights.push(spot);
    });

    // 7. Holographic Sonar Pulse Radar Dome
    const pulseGeo = new THREE.SphereGeometry(this.cellSize * 1.6, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    const pulseMat = new THREE.MeshBasicMaterial({
      color: 0x40c8e0,
      transparent: true,
      opacity: 0.0,
      wireframe: true,
      side: THREE.DoubleSide,
    });
    this.sonarPulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    this.sonarPulseMesh.position.y = 0.5;
    this.roverGroup.add(this.sonarPulseMesh);

    // Initial positioning
    const start3D = this.gridTo3D(0, 0);
    this.roverGroup.position.copy(start3D);
    this.roverPosCurrent.copy(start3D);
    this.roverPosTarget.copy(start3D);
    this.scene.add(this.roverGroup);

    // Tire Tracks Polyline
    const trackMat = new THREE.LineBasicMaterial({ color: 0x4d1606, linewidth: 3 });
    const trackGeo = new THREE.BufferGeometry().setFromPoints([start3D.clone()]);
    this.tireTracksLine = new THREE.Line(trackGeo, trackMat);
    this.scene.add(this.tireTracksLine);
    this.tireTrackPoints.push(start3D.clone());
  }

  // --------------------------------------------------------------------------
  // Landmark, Hazard, and Fog-of-War Mesh Creation
  // --------------------------------------------------------------------------
  _createLandmarks(startPos, goalPos) {
    // 1. Landing Base Pad at Start (0,0)
    const s3d = this.gridTo3D(startPos[0], startPos[1]);
    const padGeo = new THREE.CylinderGeometry(this.cellSize * 0.38, this.cellSize * 0.42, 0.4, 8);
    const padMat = new THREE.MeshStandardMaterial({ color: 0x222b3a, metalness: 0.8, roughness: 0.3 });
    const pad = new THREE.Mesh(padGeo, padMat);
    pad.position.set(s3d.x, 0.2, s3d.z);
    pad.receiveShadow = true;
    this.scene.add(pad);

    // Landing Lights Ring
    for (let i = 0; i < 8; i++) {
      const ang = (i / 8) * Math.PI * 2;
      const lx = s3d.x + Math.cos(ang) * (this.cellSize * 0.36);
      const lz = s3d.z + Math.sin(ang) * (this.cellSize * 0.36);
      const bulb = new THREE.Mesh(
        new THREE.SphereGeometry(0.2, 8, 8),
        new THREE.MeshBasicMaterial({ color: 0xf5d741 })
      );
      bulb.position.set(lx, 0.45, lz);
      this.scene.add(bulb);
    }

    // 2. Extraction Beacon Tower at Goal (N-1, N-1)
    const g3d = this.gridTo3D(goalPos[0], goalPos[1]);
    const towerGeo = new THREE.CylinderGeometry(0.8, 1.8, 8.0, 6);
    const towerMat = new THREE.MeshStandardMaterial({ color: 0x26384a, metalness: 0.9 });
    const tower = new THREE.Mesh(towerGeo, towerMat);
    tower.position.set(g3d.x, 4.0, g3d.z);
    tower.castShadow = true;
    this.scene.add(tower);

    // Glowing Core Sphere
    const coreMesh = new THREE.Mesh(
      new THREE.SphereGeometry(1.2, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0x40c8e0 })
    );
    coreMesh.position.set(g3d.x, 8.2, g3d.z);
    this.scene.add(coreMesh);

    // Skyward Orbital Beacon Beam (Laser cylinder into space)
    const beamGeo = new THREE.CylinderGeometry(0.3, 0.8, 150, 16);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0x40c8e0,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
    });
    const beam = new THREE.Mesh(beamGeo, beamMat);
    beam.position.set(g3d.x, 75, g3d.z);
    this.scene.add(beam);
  }

  _createFogOfWar() {
    this.fogBlocks.forEach((mesh) => this.scene.remove(mesh));
    this.fogBlocks.clear();

    for (let x = 0; x < this.gridSize; x++) {
      for (let y = 0; y < this.gridSize; y++) {
        // Start and Goal are always revealed
        if ((x === 0 && y === 0) || (x === this.gridSize - 1 && y === this.gridSize - 1)) {
          continue;
        }
        const cell3d = this.gridTo3D(x, y);
        const fogGeo = new THREE.BoxGeometry(this.cellSize * 0.98, 4.5, this.cellSize * 0.98);
        const fogMat = new THREE.MeshStandardMaterial({
          color: 0x1e1210, // Dark Martian sandstorm
          transparent: true,
          opacity: 0.92,
          roughness: 1.0,
        });
        const fogMesh = new THREE.Mesh(fogGeo, fogMat);
        fogMesh.position.set(cell3d.x, 2.2, cell3d.z);
        this.scene.add(fogMesh);
        this.fogBlocks.set(`${x},${y}`, fogMesh);
      }
    }
  }

  _revealFogAt(x, y) {
    const key = `${x},${y}`;
    if (this.fogBlocks.has(key)) {
      const fogMesh = this.fogBlocks.get(key);
      // Animate dissolve
      let scale = 1.0;
      const dissolveAnim = () => {
        scale -= 0.08;
        if (scale > 0) {
          fogMesh.scale.set(scale, scale, scale);
          fogMesh.material.opacity = scale * 0.9;
          requestAnimationFrame(dissolveAnim);
        } else {
          this.scene.remove(fogMesh);
          this.fogBlocks.delete(key);
        }
      };
      dissolveAnim();
    }
  }

  _createHazardMesh(x, y) {
    const key = `${x},${y}`;
    if (this.hazardMeshes.has(key)) return;

    const p3d = this.gridTo3D(x, y);
    const group = new THREE.Group();

    // 1. Sunken Acid Fluid Pool
    const poolGeo = new THREE.CylinderGeometry(this.cellSize * 0.35, this.cellSize * 0.4, 0.4, 16);
    const poolMat = new THREE.MeshStandardMaterial({
      color: 0x22ff44, // Glowing toxic green
      emissive: 0x118822,
      emissiveIntensity: 0.6,
      roughness: 0.1,
    });
    const pool = new THREE.Mesh(poolGeo, poolMat);
    pool.position.set(p3d.x, 0.2, p3d.z);
    group.add(pool);

    // 2. Floating 3D Warning Triangle
    const triGeo = new THREE.ConeGeometry(1.2, 2.0, 3);
    const triMat = new THREE.MeshStandardMaterial({
      color: 0xeb732d,
      emissive: 0xeb732d,
      emissiveIntensity: 0.5,
    });
    const tri = new THREE.Mesh(triGeo, triMat);
    tri.position.set(p3d.x, 3.5, p3d.z);
    group.add(tri);

    this.scene.add(group);
    this.hazardMeshes.set(key, { group, tri, pool });
  }

  _createRadiationMesh(x, y) {
    const key = `${x},${y}`;
    if (this.radiationMeshes.has(key)) return;

    const p3d = this.gridTo3D(x, y);
    const group = new THREE.Group();

    // 1. Swirling Volumetric Energy Sphere
    const radGeo = new THREE.SphereGeometry(2.0, 16, 16);
    const radMat = new THREE.MeshBasicMaterial({
      color: 0xf5d741,
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    });
    const radSphere = new THREE.Mesh(radGeo, radMat);
    radSphere.position.set(p3d.x, 2.8, p3d.z);
    group.add(radSphere);

    // 2. Rotating Hazard Trefoil Ring
    const ringGeo = new THREE.TorusGeometry(2.5, 0.12, 8, 24);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xeb732d });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 3;
    ring.position.set(p3d.x, 2.8, p3d.z);
    group.add(ring);

    this.scene.add(group);
    this.radiationMeshes.set(key, { group, radSphere, ring });
  }

  gridTo3D(gx, gy) {
    return new THREE.Vector3(
      this.gridOriginX + gx * this.cellSize,
      0.2,
      this.gridOriginZ + gy * this.cellSize
    );
  }

  // --------------------------------------------------------------------------
  // Server REST API Integration
  // --------------------------------------------------------------------------
  async _fetchInitState() {
    try {
      const res = await fetch("/api/init");
      const data = await res.json();
      this.gridSize = data.size;
      this.solvablePathLength = data.path_length;
      this.latestTelemetry = data;

      // Initialize Landmarks & Fog
      this._createLandmarks(data.start_pos, data.goal_pos);
      this._createFogOfWar();
      this._revealFogAt(0, 0);

      this._updateHUDInit(data);
    } catch (e) {
      console.error("Failed to connect to /api/init", e);
    }
  }

  async _executeStep() {
    if (this.isFinished || this.moveProgress < 1.0 || this.animationQueue.length > 0) {
      return;
    }

    try {
      const res = await fetch("/api/step", { method: "POST" });
      const stepData = await res.json();

      if (stepData.is_done) {
        this.isFinished = true;
        this._updateHUDDone(stepData);
        if (stepData.reached_goal) soundEngine.playVictoryChime();
        return;
      }

      this._processStepData(stepData);
    } catch (e) {
      console.error("Failed to execute /api/step", e);
    }
  }

  async _resetMission() {
    soundEngine.playClick();
    try {
      const res = await fetch("/api/reset", { method: "POST" });
      const data = await res.json();

      // Clear 3D Hazard & Radiation Overlays
      this.hazardMeshes.forEach((h) => this.scene.remove(h.group));
      this.hazardMeshes.clear();
      this.radiationMeshes.forEach((r) => this.scene.remove(r.group));
      this.radiationMeshes.clear();

      // Reset Fog & Rover position
      this._createFogOfWar();
      this._revealFogAt(0, 0);

      const start3D = this.gridTo3D(0, 0);
      this.roverGroup.position.copy(start3D);
      this.roverPosCurrent.copy(start3D);
      this.roverPosTarget.copy(start3D);
      this.roverCurrentHeading = 0.0;
      this.roverTargetHeading = 0.0;
      this.roverGroup.rotation.y = 0.0;
      this.moveProgress = 1.0;
      this.animationQueue = [];
      this.isFinished = false;

      // Reset tire tracks
      this.tireTrackPoints = [start3D.clone()];
      this.tireTracksLine.geometry.setFromPoints(this.tireTrackPoints);

      this._updateHUDInit(data);
    } catch (e) {
      console.error("Failed to reset mission", e);
    }
  }

  _processStepData(step) {
    this.latestTelemetry = step;
    const [rx, ry] = step.rover_pos;
    const target3D = this.gridTo3D(rx, ry);

    // 1. Reveal Sensed Cells in 3D
    if (step.sensed_cells) {
      step.sensed_cells.forEach(([sx, sy]) => {
        this._revealFogAt(sx, sy);
      });
    }

    // 2. Spawn 3D Hazard / Radiation Markers if detected
    if (step.known_hazard) {
      step.known_hazard.forEach(([hx, hy]) => this._createHazardMesh(hx, hy));
    }
    if (step.known_radiation) {
      step.known_radiation.forEach(([rx, ry]) => this._createRadiationMesh(rx, ry));
    }

    // 3. Sonar Radar Pulse FX & Sound
    this._triggerSonarSweep();
    soundEngine.playSonarPing();

    // 4. Handle Hazard Avoidance Sounds
    if (step.hazard_avoidance_events && step.hazard_avoidance_events.length > 0) {
      const lastEvent = step.hazard_avoidance_events[step.hazard_avoidance_events.length - 1];
      if (lastEvent[0] === step.step) {
        soundEngine.playHazardKlaxon();
      }
    }

    // 5. Setup Rover Movement Animation
    if (step.action_type === "BACKTRACK" && step.path && step.path.length > 1) {
      this.animationQueue = step.path.slice(1).map(([x, y]) => this.gridTo3D(x, y));
      this._startNextPathLeg();
    } else {
      this.roverPosTarget.copy(target3D);
      this.moveProgress = 0.0;
      const dx = target3D.x - this.roverPosCurrent.x;
      const dz = target3D.z - this.roverPosCurrent.z;
      if (dx !== 0 || dz !== 0) {
        this.roverTargetHeading = Math.atan2(dx, dz);
      }
    }

    // 6. Update HUD Telemetry
    this._updateHUDStep(step);
  }

  _startNextPathLeg() {
    if (this.animationQueue.length > 0) {
      const nextTarget = this.animationQueue.shift();
      this.roverPosTarget.copy(nextTarget);
      this.moveProgress = 0.0;
      const dx = nextTarget.x - this.roverPosCurrent.x;
      const dz = nextTarget.z - this.roverPosCurrent.z;
      if (dx !== 0 || dz !== 0) {
        this.roverTargetHeading = Math.atan2(dx, dz);
      }
    }
  }

  _triggerSonarSweep() {
    let s = 0.1;
    this.sonarPulseMesh.material.opacity = 0.55;
    const pulseAnim = () => {
      s += 0.08;
      this.sonarPulseMesh.scale.set(s, s, s);
      this.sonarPulseMesh.material.opacity = Math.max(0.0, 0.55 * (1.0 - s / 1.6));
      if (s < 1.6) {
        requestAnimationFrame(pulseAnim);
      }
    };
    pulseAnim();
  }

  // --------------------------------------------------------------------------
  // User Interface Events & Binding
  // --------------------------------------------------------------------------
  _initUIEvents() {
    // Regenerate Button
    document.getElementById("btn-regenerate").addEventListener("click", () => this._resetMission());

    // Pause Toggle
    const pauseBtn = document.getElementById("btn-pause");
    pauseBtn.addEventListener("click", () => {
      this.isPaused = !this.isPaused;
      pauseBtn.textContent = this.isPaused ? "[SPACE] Resume" : "[SPACE] Pause";
      this._updateStatusBadge(this.isPaused ? "PAUSED" : "NAVIGATING TO GOAL");
    });

    // Sound Toggle
    const soundBtn = document.getElementById("btn-sound");
    soundBtn.addEventListener("click", () => {
      soundEngine.init();
      const on = soundEngine.toggle();
      soundBtn.textContent = on ? "🔊 Sound ON" : "🔇 Sound OFF";
    });

    // Speed Slider
    const speedSlider = document.getElementById("speed-slider");
    const speedVal = document.getElementById("speed-val");
    const updateSpeed = (val) => {
      this.speedMultiplier = parseFloat(val);
      speedSlider.value = val;
      speedVal.textContent = `${this.speedMultiplier.toFixed(2)}x`;
    };
    speedSlider.addEventListener("input", (e) => updateSpeed(e.target.value));
    document.getElementById("btn-speed-minus").addEventListener("click", () => {
      updateSpeed(Math.max(0.25, this.speedMultiplier - 0.25));
    });
    document.getElementById("btn-speed-plus").addEventListener("click", () => {
      updateSpeed(Math.min(4.0, this.speedMultiplier + 0.25));
    });

    // Camera Mode Switcher
    const camButtons = document.querySelectorAll(".btn-cam");
    camButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        camButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.cameraMode = btn.dataset.cam;
        this.orbitControls.enabled = this.cameraMode === "orbit";

        const cockpit = document.getElementById("cockpit-overlay");
        if (this.cameraMode === "mast") {
          cockpit.classList.remove("hidden");
        } else {
          cockpit.classList.add("hidden");
        }
      });
    });

    // Keyboard Shortcuts
    window.addEventListener("keydown", (e) => {
      if (e.code === "Space") {
        e.preventDefault();
        pauseBtn.click();
      } else if (e.code === "ArrowRight") {
        if (this.isPaused) this._executeStep();
      } else if (e.key === "r" || e.key === "R") {
        this._resetMission();
      } else if (e.key === "c" || e.key === "C") {
        const modes = ["chase", "satellite", "mast", "orbit"];
        const nextIdx = (modes.indexOf(this.cameraMode) + 1) % modes.length;
        document.querySelector(`.btn-cam[data-cam="${modes[nextIdx]}"]`).click();
      } else if (e.key === "g" || e.key === "G") {
        this.showDebugGrid = !this.showDebugGrid;
        this.gridLinesGroup.visible = this.showDebugGrid;
      } else if (e.key === "+" || e.key === "=") {
        document.getElementById("btn-speed-plus").click();
      } else if (e.key === "-") {
        document.getElementById("btn-speed-minus").click();
      }
    });

    // Unlock Web Audio on first user interaction
    window.addEventListener("click", () => soundEngine.init(), { once: true });
  }

  // --------------------------------------------------------------------------
  // HUD Telemetry Updates
  // --------------------------------------------------------------------------
  _updateHUDInit(data) {
    document.getElementById("telem-step").textContent = "0";
    document.getElementById("telem-pos").textContent = "(0, 0)";
    const gx = data.goal_pos[0];
    const gy = data.goal_pos[1];
    document.getElementById("telem-goal").textContent = `(${gx}, ${gy}) [d=${gx + gy}]`;
    document.getElementById("telem-kb").textContent = data.kb_clauses;
    document.getElementById("avoid-hazards").innerHTML = `<span class="symbol-icon">▲</span> 0`;
    document.getElementById("avoid-radiation").innerHTML = `<span class="symbol-icon">☢</span> 0`;
    document.getElementById("progress-desc").textContent = `Start (0,0) → Goal (${gx},${gy}) | Path: 100% Solvable`;
    document.getElementById("progress-pct").textContent = "0%";
    document.getElementById("progress-bar-fill").style.width = "0%";

    this._updateStatusBadge("NAVIGATING TO GOAL");
    this._setDecisionBanner("DECIDE", "Rover landed. Planning logical resolution path...");
    this._appendLogLine(`[INIT] Seed: ${data.seed} | Solvable Path: ${data.path_length} cells`, "text-cyan");
  }

  _updateHUDStep(step) {
    document.getElementById("telem-step").textContent = step.step;
    document.getElementById("telem-pos").textContent = `(${step.rover_pos[0]}, ${step.rover_pos[1]})`;

    const gx = this.gridSize - 1;
    const gy = this.gridSize - 1;
    const dist = Math.abs(step.rover_pos[0] - gx) + Math.abs(step.rover_pos[1] - gy);
    document.getElementById("telem-goal").textContent = `(${gx}, ${gy}) [d=${dist}]`;
    document.getElementById("telem-kb").textContent = step.kb_clause_count;

    // Avoidance Counters
    const avoidHaz = (step.hazard_avoidance_events || []).filter((e) => e[3] === "Hazard").length;
    const avoidRad = (step.hazard_avoidance_events || []).filter((e) => e[3] === "Radiation").length;
    document.getElementById("avoid-hazards").innerHTML = `<span class="symbol-icon">▲</span> ${avoidHaz}`;
    document.getElementById("avoid-radiation").innerHTML = `<span class="symbol-icon">☢</span> ${avoidRad}`;

    // Progress Bar
    const maxDist = (this.gridSize - 1) * 2;
    const pct = step.reached_goal ? 100 : Math.max(0, Math.min(100, Math.round(((maxDist - dist) / maxDist) * 100)));
    document.getElementById("progress-pct").textContent = `${pct}%`;
    document.getElementById("progress-bar-fill").style.width = `${pct}%`;

    // Status Badge & Banner
    if (step.action_type === "BACKTRACK") {
      this._updateStatusBadge("REROUTING / BACKTRACK", "hazard");
      this._setDecisionBanner("BACKTRACK", step.decision_text);
    } else if (step.action_type === "MOVE") {
      this._updateStatusBadge("NAVIGATING TO GOAL");
      this._setDecisionBanner("DECIDE", step.decision_text);
    }

    // Inference Logs
    const pCount = Object.keys(step.percepts || {}).length;
    this._appendLogLine(`[Step ${step.step}] PERCEIVE: ${pCount} signals`, "text-cyan");
    if (step.tell_log && step.tell_log.length > 0) {
      const infCount = step.tell_log.reduce((acc, t) => acc + t.inferred.length, 0);
      if (infCount > 0) {
        this._appendLogLine(`[Step ${step.step}] TELL: +${infCount} inferred facts via KB`, "text-orange");
      }
    }
    if (step.action_type === "MOVE") {
      this._appendLogLine(`[Step ${step.step}] ASK: Safe? -> TRUE (entailed)`, "text-green");
    }
  }

  _updateHUDDone(step) {
    if (step.reached_goal) {
      this._updateStatusBadge("EXTRACTION GOAL REACHED!", "goal");
      this._setDecisionBanner("SUCCESS", "Extraction beacon activated! Mission 100% Successful.");
      this._appendLogLine("[MISSION COMPLETE] Goal Reached Successfully!", "text-green");
    } else {
      this._updateStatusBadge("MISSION FINISHED", "paused");
    }
  }

  _updateStatusBadge(text, type = "normal") {
    const badge = document.getElementById("status-badge");
    badge.textContent = text;
    badge.className = `status-badge ${type}`;
  }

  _setDecisionBanner(tag, text) {
    document.getElementById("decision-tag").textContent = tag;
    document.getElementById("decision-text").textContent = text;
  }

  _appendLogLine(text, colorClass = "text-muted") {
    const feed = document.getElementById("log-feed");
    const div = document.createElement("div");
    div.className = `log-line ${colorClass}`;
    div.textContent = text;
    feed.appendChild(div);
    feed.scrollTop = feed.scrollHeight;
  }

  // --------------------------------------------------------------------------
  // Main Animation & Render Loop
  // --------------------------------------------------------------------------
  _animate(nowMs) {
    requestAnimationFrame((t) => this._animate(t));

    const dt = this.clock.getDelta();
    const nowSec = nowMs / 1000;

    // 1. Logic Step Execution
    const effectiveDelay = this.baseStepDelay / Math.max(0.1, this.speedMultiplier);
    if (!this.isPaused && !this.isFinished) {
      if (this.moveProgress >= 1.0 && this.animationQueue.length === 0) {
        if (nowSec - this.lastStepTime >= effectiveDelay) {
          this._executeStep();
          this.lastStepTime = nowSec;
        }
      }
    }

    // 2. Rover Position Interpolation
    const isMoving = this.moveProgress < 1.0;
    soundEngine.setMotorRunning(isMoving, this.speedMultiplier);

    if (isMoving) {
      this.moveProgress = Math.min(1.0, this.moveProgress + this.moveSpeed * this.speedMultiplier * dt);
      const easeT = this.moveProgress * this.moveProgress * (3.0 - 2.0 * this.moveProgress);

      this.roverPosCurrent.lerpVectors(this.roverPosCurrent, this.roverPosTarget, easeT);
      this.roverGroup.position.copy(this.roverPosCurrent);

      // Rotate Wheels & Steer
      this.roverWheels.forEach((w) => {
        w.mesh.rotation.y += 12.0 * dt * this.speedMultiplier;
      });

      // Heading rotation
      this.roverCurrentHeading += (this.roverTargetHeading - this.roverCurrentHeading) * 0.15;
      this.roverGroup.rotation.y = this.roverCurrentHeading;

      // Append persistent tire tracks
      const lastPt = this.tireTrackPoints[this.tireTrackPoints.length - 1];
      if (lastPt.distanceTo(this.roverPosCurrent) > 0.8) {
        this.tireTrackPoints.push(this.roverPosCurrent.clone());
        this.tireTracksLine.geometry.setFromPoints(this.tireTrackPoints);
      }

      if (this.moveProgress >= 1.0) {
        this.roverPosCurrent.copy(this.roverPosTarget);
        if (this.animationQueue.length > 0) {
          this._startNextPathLeg();
        }
      }
    }

    // 3. Hazard & Radiation Animations
    this.hazardMeshes.forEach((h) => {
      h.tri.rotation.y += 1.5 * dt;
    });
    this.radiationMeshes.forEach((r) => {
      r.radSphere.rotation.y += 1.2 * dt;
      r.ring.rotation.z += 2.0 * dt;
    });

    // 4. Update Camera Mode
    this._updateCamera(dt);

    // 5. Render Scene
    this.renderer.render(this.scene, this.camera);
  }

  _updateCamera(dt) {
    const rpos = this.roverGroup.position;

    if (this.cameraMode === "chase") {
      // Cinematic Chase Cam behind rover
      const offset = new THREE.Vector3(
        -Math.sin(this.roverCurrentHeading) * 20,
        10,
        -Math.cos(this.roverCurrentHeading) * 20
      );
      const camTargetPos = rpos.clone().add(offset);
      this.camera.position.lerp(camTargetPos, 0.08);
      this.camera.lookAt(rpos.x, rpos.y + 1.5, rpos.z);

    } else if (this.cameraMode === "satellite") {
      // Top-down tactical overview
      const satPos = new THREE.Vector3(0, 70, 45);
      this.camera.position.lerp(satPos, 0.08);
      this.camera.lookAt(0, 0, 0);

    } else if (this.cameraMode === "mast") {
      // First-person MastCam FPV
      const mastPos = rpos.clone().add(new THREE.Vector3(0, 3.2, 0));
      this.camera.position.copy(mastPos);
      const forward = new THREE.Vector3(
        Math.sin(this.roverCurrentHeading) * 15,
        -0.5,
        Math.cos(this.roverCurrentHeading) * 15
      );
      this.camera.lookAt(mastPos.clone().add(forward));

    } else if (this.cameraMode === "orbit") {
      this.orbitControls.target.copy(rpos);
      this.orbitControls.update();
    }
  }
}

// Start application when DOM loads
window.addEventListener("DOMContentLoaded", () => {
  new MarsRover3DApp();
});
