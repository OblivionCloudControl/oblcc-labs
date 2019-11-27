import React, { Component } from "react";
import "./Home.scss";
import { Form, FormGroup, Input } from "reactstrap";

import { OneColumnLayout } from "../components/layouts/OneColumnLayout";
import { Button } from "../components/forms/Button";
import qs from "query-string";

import beaver from "../assets/beaver.png";
import config from "../config";

export default class Home extends Component {
  constructor(props) {
    super(props);
    this.state = {
      name : '',
      inspector : false,
    };
  }

  handleChange = event => {
    this.setState({
      name : event.target.value
    });
  };

  componentDidMount() {
    fetch('inspector.json')
      .then(resp => resp.json())
      .then(data => {
        console.log("data = ", data);
        this.setState({inspector : data.done});
      })
      .catch(err => {
        console.error('fetching inspector.json fails:', err);
      });
  }

  render() {

    const isInspectorStepDone = this.state.inspector;
    const query = this.props.location.search;
    const queryParams = qs.parse(query);
    const queryName = queryParams.name;

    let notDoneMessages = [];


    if(!isInspectorStepDone) {
      notDoneMessages.push('You haven\'t completed the Inspector step yet');
    }

    if(config.ACCESS_KEY) {
      notDoneMessages.push('You haven\'t completed the Static Code Analysis step yet');
    }


    const inputForm = (
      <Form className="center-form">
        <FormGroup>
          <div className="instruction-text">Please enter your name:</div>
          <Input className="input-text" type="string" name="name" id="name" placeholder="ex. John Adam"
                 onChange={this.handleChange}/>
        </FormGroup>
        <Button className="submit-btn" color="primary">Submit</Button>
      </Form>
    );

    let content = null;
    if (queryName && notDoneMessages.length === 0) {
      content = (
        <div className="center-container">
          <div className="center-beaver">
            <img src={beaver} alt="Solutions Prototyping Beaver Logo"/>
            <h2>Congratulations, {queryName} </h2>
            <div>You have completed SEC332! You are now a DevSecOps guru.</div>
            <div>Show this page to our staff to get your sticker.</div>
          </div>
        </div>
      );
    } else {
      content = (
        <div className="center-container">
          <h1>Congratulations, your site is up and running!</h1>

          { notDoneMessages.length > 0 &&
            <div className="almost-there">
              <p>Steps left:</p>
              <ul className="not-done">
                {notDoneMessages.map(msg => <li key={msg}>{msg}</li>)}
              </ul>
              <p className="text-info">*Don't forget to recreate instance with the new AMI after you have completed those steps.</p>
            </div>
          }

          { notDoneMessages.length === 0 &&
            <div className="left-aligned-container">
              {inputForm}
            </div>
          }
        </div>
      );
    }

    return (
      <OneColumnLayout>
        {content}
      </OneColumnLayout>
    );
  }
}
