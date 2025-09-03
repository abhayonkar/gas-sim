function result = simulate_gas_transition(pipe_length, diameter, initial_pressure, flow_rate)
    % Simple Simscape model for gas transition
    % Assume model 'gas_pipe_transient.slx' with Pipe (G), Gas Properties (G)
    % Load and simulate
    load_system('gas_pipe_transient');
    set_param('gas_pipe_transient/Pipe (G)', 'Length', num2str(pipe_length));
    set_param('gas_pipe_transient/Pipe (G)', 'Diameter', num2str(diameter));
    simOut = sim('gas_pipe_transient');
    time = simOut.yout{1}.Values.Time;
    pressure = simOut.yout{1}.Values.Data;
    velocity = simOut.yout{2}.Values.Data;
    result = struct('time', time, 'pressure', pressure, 'velocity', velocity);
end